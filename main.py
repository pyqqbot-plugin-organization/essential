import datetime
import os.path
import threading
import time as timer
from API.misc import stopThread
from API.permission import Permissions
from API.plugin import Plugin, PluginHelpText
import json
from API.actions.group.message import sendGroupMessage
from API.types import GroupMessage, GroupMemberAdd
from settings import PATH, LOGGER


def sendNotice(groupId, content):
    sendGroupMessage(groupId, msg=content)


class Essential(Plugin):
    def __init__(self):
        self.notices = {}
        self.threads = {}

    def on_command_setNotice(self, command: dict, event: GroupMessage):
        # 内容: content， 时间: time， 是否提醒新成员: sendToNewMember
        if "content" not in command or "time" not in command:
            return self.setNotice_helper()
        content = command["content"]
        time = command["time"]
        groupId = event.groupId
        if time.find(":") == -1:
            return self.setNotice_helper()
        sendToNewMember = False
        if "sendToNewMember" in command:
            sendToNewMember = True
        data = json.load(open(os.path.join(PATH, "plugins/essential/notice.json"), "r", encoding="utf8"))
        if f"{groupId}" not in data:
            data[f"{groupId}"] = {"notices": {}, "_id": 0}
        data[f"{groupId}"]["_id"] += 1
        _id = data[f"{groupId}"]["_id"]
        data[f"{groupId}"]["notices"][str(_id)] = {"content": content, "time": time, "sendToNewMember": sendToNewMember,
                                                   "creator": event.sender.name + f"({event.sender.userId})"}
        json.dump(data, open(os.path.join(PATH, "plugins/essential/notice.json"), "w", encoding="utf8"), indent=4)
        self.notices = data.copy()
        if groupId not in self.threads:
            self.threads[groupId] = {}
        self.threads[groupId][_id] = threading.Thread(target=self.sendNoticeByTime, args=(str(groupId), str(_id)))
        self.threads[groupId][_id].start()
        return "设置成功"

    def setNotice_helper(self):
        text = PluginHelpText("setNotice")
        text.addArg("content", "设置公告的内容", "公告的内容", ["string"], isBoolArg=False)
        text.addArg("time", "设置公告发送的时间", "小时:分(英文冒号)", ["string"], isBoolArg=False)
        text.addArg("sendToNewMember", "是否提醒新成员", "", [], isBoolArg=True, isNeeded=False)
        text.addExample("-content:114514,1919810 -time:1:0", "每天凌晨1发公告")
        text.addExample("-content:114514,1919810 -time:1:0 -sendToNewMember", "每天凌晨1发公告, 但是新成员也提醒")
        text.addExample("-content:`aaaaaaaaaa bbbbbbbbbbb cccccccc \n cccccccccc` -time:1:0 -sendToNewMember",
                        "每天凌晨1发公告, 但是新成员也提醒")
        return text.generate()

    def get_permission_setNotice(self):
        return Permissions.admin

    def on_load(self):
        data = json.load(open(os.path.join(PATH, "plugins/essential/notice.json"), "r", encoding="utf8"))
        self.notices = data
        for group in self.notices:
            for i in self.notices[group]["notices"]:
                if int(group) not in self.threads:
                    self.threads[int(group)] = {}
                self.threads[int(group)][i] = threading.Thread(target=self.sendNoticeByTime, args=(group, i))
                self.threads[int(group)][i].start()

    def on_remove(self):
        for group in self.threads:
            for thread in self.threads[group]:
                stopThread(self.threads[group][thread])

    def on_group_member_add(self, event: GroupMemberAdd):
        for notice in self.notices[str(event.groupId)]:
            if notice["sendToNewMember"]:
                sendNotice(str(event.groupId), notice["content"])

    def sendNoticeByTime(self, groupId, i):
        # print(self.notices)
        time = self.notices[groupId]["notices"][i]["time"].split(":")
        hour = int(time[0])
        minute = int(time[1])
        while 1:
            # print(datetime.datetime.now().hour, datetime.datetime.now().minute)
            while not (datetime.datetime.now().minute == minute and datetime.datetime.now().hour == hour): timer.sleep(
                5)
            sendNotice(int(groupId), self.notices[groupId]["notices"][i]["content"])
            while not (datetime.datetime.now().minute != minute and datetime.datetime.now().hour != hour): timer.sleep(
                5)

    def on_command_getNotice(self, command: dict, event: GroupMessage):
        if str(event.groupId) not in self.notices:
            return "null"
        groupNotices = self.notices[str(event.groupId)]["notices"]
        text = "\n"
        for i in groupNotices:
            text += f"id:{i}\ntime:{groupNotices[i]['time']}\ncreator:{groupNotices[i]['creator']}\ncontent:{groupNotices[i]['content']}\n\n"
        return text

    def get_permission_getNotice(self):
        return Permissions.member

    def getNotice_helper(self):
        text = PluginHelpText("getNotice")
        text.addExample("", "发送所有的公告信息")
        return text.generate()

    def on_command_removeNotice(self, command: dict, event: GroupMessage):
        if "id" not in command:
            return self.removeNotice_helper()
        _id = command["id"]
        groupId = event.groupId
        if str(event.groupId) not in self.notices:
            return "这个群没公告"
        LOGGER.info(self.notices[str(event.groupId)]["notices"])
        if _id not in self.notices[str(event.groupId)]["notices"]:
            return "没有这个公告"
        stopThread(self.threads[groupId][_id])
        self.notices[str(event.groupId)]["notices"].pop(_id)
        json.dump(self.notices, open(os.path.join(PATH, "plugins/essential/notice.json"), "w", encoding="utf8"), indent=4)
        return "删除成功"

    def get_permission_removeNotice(self):
        return Permissions.admin

    def removeNotice_helper(self):
        text = PluginHelpText("removeNotice")
        text.addArg("id", "notice的id值", "id值", ["int"], False)
        text.addExample("-id:114514", "删除id为114514的notice")
        return text.generate()
