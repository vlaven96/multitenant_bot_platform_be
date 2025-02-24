from enum import Enum

class RequestAction(Enum):
    LoginWithPassword = "LoginWithPassword"
    ArgosGetToken = "ArgosGetToken"
    FideliusPollRecrypt = "FideliusPollRecrypt"
    AddFriends = "AddFriends"
    RemoveFriends = "RemoveFriends"
    SyncConversations = "SyncConversations"
    GetUploadLocationsByKey = "GetUploadLocationsByKey"
    CreateContentMessage = "CreateContentMessage"
    SendODLVCode = "SendODLVCode"
    VerifyODLVCode = "VerifyODLVCode"
    DeltaSync = "DeltaSync"
    BatchDeltaSync = "BatchDeltaSync"
    Search = "Search"
    CheckUsername = "CheckUsername"
    SetDisplayName = "SetDisplayName"
    UpdateEmail = "UpdateEmail"
    VerifyChallenge = "VerifyChallenge"
    QueryMessages = "QueryMessages"
    GetSelfAvatar = "GetSelfAvatar"
    GetFriendsUserScore = "GetFriendsUserScore"
    GetStories = "GetStories"
    SendTypingNotification = "SendTypingNotification"
    UpdateConversation = "UpdateConversation"
    QueryConversations = "QueryConversations"
    UpdateContentMessage = "UpdateContentMessage"
    VerifyTwoFA = "VerifyTwoFA"
    ChangeUsername = "ChangeUsername"
    DeepLinkRequest = "DeepLinkRequest"
    GetSnapchattersPublicInfo = "GetSnapchattersPublicInfo"
    ScReAuth = "ScReAuth"
    SyncCustomStoryGroups = "SyncCustomStoryGroups"
    DeleteCustomStoryGroup = "DeleteCustomStoryGroup"
    CreateCustomStoryGroup = "CreateCustomStoryGroup"

    def to_decode_type(self):
        mapping = {
            "GetSnapchattersPublicInfo": 999,
            "DeepLinkRequest": 999,
            "ScReAuth": 999,
            "FideliusPollRecrypt": 0,
            "LoginWithPassword": 1,
            "ArgosGetToken": 2,
            "AddFriends": 0, # 3
            "RemoveFriends": 4,
            "SyncConversations": 5,
            "GetUploadLocationsByKey": 6,
            "CreateContentMessage": 7,
            "SendODLVCode": 8,
            "VerifyODLVCode": 9,
            "DeltaSync": 10,
            "BatchDeltaSync": 11,
            "Search": 12,
            "CheckUsername": 13,
            "SetDisplayName": 15,
            "UpdateEmail": 16,
            "VerifyChallenge": 17,
            "QueryMessages": 18,
            "GetSelfAvatar": 19,
            "GetAvatar": 20,
            "GetFriendsUserScore": 21,
            "GetStories": 23,
            "SendTypingNotification": 24,
            "UpdateConversation": 25,
            "QueryConversations": 26,
            "UpdateContentMessage": 27,
            "VerifyTwoFA": 28,
            "ChangeUsername": 29,
            "SyncCustomStoryGroups": 30,
            "DeleteCustomStoryGroup": 999,
            "CreateCustomStoryGroup": 32,
        }
        return mapping.get(self.value, 0)

    def should_include_device(self):
        mapping = {
            "QueryMessages": True,
            "ChangeUsername": True,
            "DeltaSync": True,
            "BatchDeltaSync": True,
        }
        return mapping.get(self.value, 0)