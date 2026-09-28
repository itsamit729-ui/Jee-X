"""Self-service teacher enrollment; admin removals remain enforceable."""
import secrets
from fastapi import HTTPException
from app import models as m
from app.auth import utcnow


def enable_teacher(db, account):
    account = db.query(m.AuthAccount).filter_by(id=account.id).with_for_update().populate_existing().one()
    if account.disabled:
        raise HTTPException(403, 'This account is disabled.')
    if account.user_id:
        user = db.query(m.User).filter_by(id=account.user_id).with_for_update().populate_existing().one()
        if user.status != 'active':
            raise HTTPException(403, 'This account is suspended.')
    else:
        user = m.User(auth0_sub='local:' + account.id, email=account.email,
            name=account.email.split('@')[0], username='teacher_' + secrets.token_hex(8), role='student', status='active')
        db.add(user)
        db.flush()
        account.user_id = user.id
    access = db.get(m.TeacherAccess, user.id, populate_existing=True)
    if access:
        if not access.active:
            raise HTTPException(403, 'Teacher access was removed from this account. Contact support to restore it.')
        return user
    db.add(m.TeacherAccess(user_id=user.id, active=True, granted_at=utcnow()))
    db.add(m.AuditLog(actor_id=user.id, action='teacher_self_enrolled', entity='user', entity_id=user.id,
        before={'active': False}, after={'active': True}, reason='Account owner selected teacher mode.'))
    return user
