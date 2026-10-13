"""Authenticated teacher profile; never requires a student profile."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from app import models as m
from app.database import get_db
from app.routers.teaching import require_teacher
from app.routers.public_profiles import store_avatar_image

router=APIRouter(prefix='/api/teacher',tags=['teacher profile'])

class ProfileIn(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=100)
    institution:str=Field('',max_length=150)
    subjects:list[str]=Field(default_factory=list,max_length=10)
    bio:str=Field('',max_length=1000)
    version:int=Field(ge=0)

@router.get('/profile')
def profile(user=Depends(require_teacher),db=Depends(get_db)):
    row=db.get(m.TeacherProfile,user.id)
    return {'name':user.name,'username':user.username,'email':user.email,'institution':(row.details or {}).get('institution','') if row else '',
        'subjects':(row.details or {}).get('subjects',[]) if row else [],'bio':(row.details or {}).get('bio','') if row else '',
        'version':row.version if row else 0,'avatar_url':'/api/teacher/profile/avatar' if db.get(m.ProfileAvatar,user.id) else None,
        'access':'active'}

@router.put('/profile')
def save_profile(body:ProfileIn,user=Depends(require_teacher),db=Depends(get_db)):
    if any(s not in ('Physics','Chemistry','Mathematics','English','Logical reasoning','Biology') for s in body.subjects):
        raise HTTPException(422,'Choose subjects from the list.')
    row=db.get(m.TeacherProfile,user.id)
    if body.version!=(row.version if row else 0): raise HTTPException(409,'Your profile changed in another window. Reload before saving.')
    if row is None:
        row=m.TeacherProfile(user_id=user.id,version=0);db.add(row)
    row.details={'institution':body.institution,'subjects':list(dict.fromkeys(body.subjects)),'bio':body.bio}
    row.version+=1;user.name=body.name
    db.commit();return profile(user,db)

@router.put('/profile/avatar')
async def save_photo(request:Request,response:Response,user=Depends(require_teacher),db=Depends(get_db)):
    await store_avatar_image(request,response,user,db)
    return {'avatar_url':'/api/teacher/profile/avatar'}

@router.get('/profile/avatar')
def photo(user=Depends(require_teacher),db=Depends(get_db)):
    row=db.get(m.ProfileAvatar,user.id)
    if not row: raise HTTPException(404,'No profile photo.')
    return Response(row.image,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.delete('/profile/avatar')
def delete_photo(user=Depends(require_teacher),db=Depends(get_db)):
    db.query(m.ProfileAvatar).filter_by(user_id=user.id).delete();db.commit()
    return {'avatar_url':None}
