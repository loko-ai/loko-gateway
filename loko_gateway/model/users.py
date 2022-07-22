class RoleMapping:
    def __init__(self, **roles):
        self.roles = roles

    def set(self, role, level):
        self.roles[role] = level

    def get(self, role):
        return self.roles[role]


class User:
    def __init__(self,id:str=None, name:str=None, family_name:str=None, username: str=None, password: str=None, email:str=None, location:str=None, company:str=None,role: str = None, avatar=None, newsletter:bool=False, privacy_policy_agreement:bool=False):
        self.id = id or email
        self.name = name or ""
        self.family_name = family_name or ""
        self.username = username or self.name
        self.password = password
        self.email = email or ""
        self.role = role or "USER"
        self.avatar = avatar or ""
        self.location = location or ""
        self.company = company or ""
        self.newsletter = newsletter or False
        self.privacy_policy_agreement = privacy_policy_agreement or False