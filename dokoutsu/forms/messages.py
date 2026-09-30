"""アカウント系・問題系のフォームで共通に使うエラー文言。"""

# Djangoの既定の文言(「このフィールドは必須です。」等)は詳細設計書の文言と異なるため、
# エラーの種類ごとに差し替える。%(limit_value)d には各項目の上限・下限の数値が入る。
REQUIRED_MESSAGE = {"required": "入力してください"}
MAX_LENGTH_MESSAGE = {"max_length": "%(limit_value)d文字以内で入力してください"}
