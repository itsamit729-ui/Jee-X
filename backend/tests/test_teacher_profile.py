import io
from PIL import Image
from test_teacher_papers import studio, classroom, setup
from app import models as m
from app.routers import teacher_profile


def test_teacher_profile_is_independent_private_and_versioned(studio):
    c,factory,active,room=studio
    c.app.include_router(teacher_profile.router)
    result=c.get('/api/teacher/profile');assert result.status_code==200,result.text
    initial=result.json()
    with factory() as db:
        old_student=db.get(m.StudentProfile,3)
        old_dob=old_student.dob if old_student else None
    body={'name':'Physics Faculty','institution':'Example Coaching','subjects':['Physics'],'bio':'Concepts and classroom practice.','version':initial['version']}
    r=c.put('/api/teacher/profile',json=body);assert r.status_code==200,r.text
    assert r.json()['name']=='Physics Faculty' and r.json()['institution']=='Example Coaching'
    assert c.put('/api/teacher/profile',json=body).status_code==409
    assert c.put('/api/teacher/profile',json={**body,'name':' ','version':r.json()['version']}).status_code==422
    image=Image.new('RGB',(120,120),'orange');out=io.BytesIO();image.save(out,format='PNG')
    upload=c.put('/api/teacher/profile/avatar',content=out.getvalue(),headers={'Content-Type':'image/png'})
    assert upload.status_code==200,upload.text
    assert upload.json()['avatar_url']=='/api/teacher/profile/avatar'
    assert c.get('/api/teacher/profile/avatar').headers['content-type']=='image/jpeg'
    assert c.put('/api/teacher/profile/avatar',content=b'not an image',headers={'Content-Type':'image/png'}).status_code==422
    assert c.delete('/api/teacher/profile/avatar').status_code==200
    assert c.get('/api/teacher/profile/avatar').status_code==404
    with factory() as db:
        row=db.get(m.StudentProfile,3)
        assert (row.dob if row else None)==old_dob
        assert db.get(m.TeacherProfile,3).details['subjects']==['Physics']
    active[0]=1
    assert c.get('/api/teacher/profile').status_code==403
    assert c.put('/api/teacher/profile',json=body).status_code==403
    assert c.get('/api/teacher/profile/avatar').status_code==403
