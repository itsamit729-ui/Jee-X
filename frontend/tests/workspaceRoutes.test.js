import test from 'node:test'
import assert from 'node:assert/strict'
import { isTeacherAccount, teacherRouteRedirect } from '../src/lib/workspaceRoutes.js'

test('teacher routes replace student pages before student data is requested',()=>{
  assert.equal(isTeacherAccount({account_type:'teacher',teacher:false}),true)
  assert.equal(isTeacherAccount({teacher:true}),true)
  assert.equal(isTeacherAccount({account_type:'student'}),false)
  assert.equal(teacherRouteRedirect('/profile'),'/teacher/profile')
  assert.equal(teacherRouteRedirect('/pricing'),'/teacher/account')
  for(const path of ['/','/dashboard','/classes','/plan','/free-test','/image-questions','/syllabus','/students','/u/student','/pyq','/onboarding']) assert.equal(teacherRouteRedirect(path),'/teacher')
  for(const path of ['/teacher','/teacher/profile','/teacher/account','/notifications','/account/security','/terms','/privacy','/signup/terms']) assert.equal(teacherRouteRedirect(path),null)
})
