from app.models import Setting


def update_settings(db, data) -> Setting:
    """เขียนทุกฟิลด์จาก data ลงแถว settings id=1 แล้ว commit"""
    row = db.get(Setting, 1)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return row
