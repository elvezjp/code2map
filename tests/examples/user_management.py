"""
User Management Module
ユーザー情報の管理を行うモジュール
"""

import re
import json
from datetime import datetime
from typing import Optional


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


class UserNotFoundError(Exception):
    """ユーザーが見つからない場合のエラー"""
    pass


def validate_email(email: str) -> bool:
    """メールアドレスのバリデーション"""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def validate_age(age: int) -> bool:
    """年齢のバリデーション（0-150の範囲）"""
    return 0 <= age <= 150


class User:
    """ユーザー情報を表すクラス"""

    def __init__(self, user_id: int, name: str, email: str, age: int):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.age = age
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "age": self.age,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"User(id={self.user_id}, name={self.name}, email={self.email})"


class UserRepository:
    """ユーザーデータの永続化を担当するリポジトリ"""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    def save(self, user: User) -> User:
        """ユーザーを保存"""
        if user.user_id == 0:
            user.user_id = self._next_id
            self._next_id += 1
        user.updated_at = datetime.now()
        self._users[user.user_id] = user
        return user

    def find_by_id(self, user_id: int) -> Optional[User]:
        """IDでユーザーを検索"""
        return self._users.get(user_id)

    def find_all(self) -> list[User]:
        """全ユーザーを取得"""
        return list(self._users.values())

    def delete(self, user_id: int) -> bool:
        """ユーザーを削除"""
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False


class UserService:
    """ユーザー管理のビジネスロジックを担当するサービス"""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def create_user(self, name: str, email: str, age: int) -> User:
        """新規ユーザーを作成"""
        if not validate_email(email):
            raise ValidationError(f"Invalid email format: {email}")
        if not validate_age(age):
            raise ValidationError(f"Invalid age: {age}")

        user = User(user_id=0, name=name, email=email, age=age)
        return self.repository.save(user)

    def get_user(self, user_id: int) -> User:
        """ユーザーを取得"""
        user = self.repository.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")
        return user

    def update_user(self, user_id: int, name: str = None, email: str = None, age: int = None) -> User:
        """ユーザー情報を更新"""
        user = self.get_user(user_id)

        if name is not None:
            user.name = name
        if email is not None:
            if not validate_email(email):
                raise ValidationError(f"Invalid email format: {email}")
            user.email = email
        if age is not None:
            if not validate_age(age):
                raise ValidationError(f"Invalid age: {age}")
            user.age = age

        return self.repository.save(user)

    def delete_user(self, user_id: int) -> bool:
        """ユーザーを削除"""
        self.get_user(user_id)  # 存在確認
        return self.repository.delete(user_id)

    def list_users(self) -> list[User]:
        """全ユーザーを一覧取得"""
        return self.repository.find_all()

    def export_to_json(self) -> str:
        """全ユーザーをJSON形式でエクスポート"""
        users = self.list_users()
        return json.dumps([u.to_dict() for u in users], indent=2, ensure_ascii=False)
