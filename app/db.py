from sqlalchemy.exc import IntegrityError
...

def create_teacher(self, name: str, pin_hash: str, gemini_api_key_encrypted: str, gemini_model: str) -> Teacher:
    row = TeacherModel(
        name=name,
        pin_hash=pin_hash,
        gemini_api_key_encrypted=gemini_api_key_encrypted,
        gemini_model=gemini_model,
        created_at=datetime.utcnow(),
    )
    self.session.add(row)
    try:
        self.session.commit()
    except IntegrityError:
        self.session.rollback()
        raise HTTPException(status_code=409, detail="이미 등록된 이름이에요. 다른 이름을 쓰거나 로그인해주세요.")
    self.session.refresh(row)
    return _to_dataclass(row)
