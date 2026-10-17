export const paperExams={jee_main:'JEE Main',jee_advanced:'JEE Advanced',mht_cet:'MHT-CET',bitsat:'BITSAT'}
export const paperSubjects={PHY:'Physics',CHEM:'Chemistry',MATH:'Mathematics',ENG:'English',LR:'Logical reasoning'}
export function defaultMarking(exam,scope) {
  return exam==='mht_cet'?{correct:scope==='MATH'?2:1,wrong:0}:exam==='bitsat'?{correct:3,wrong:1}:{correct:4,wrong:1}
}
export function quickPaperProblem(form,reference) {
  if(!Number.isInteger(Number(form.duration))||Number(form.duration)<1||Number(form.duration)>240)return 'Choose a duration between 1 and 240 minutes.'
  if(form.method==='reference'&&!reference)return 'Choose a past paper from the list.'
  if(!form.fullPaper&&(!Number.isInteger(Number(form.count))||Number(form.count)<1||Number(form.count)>200))return 'Choose between 1 and 200 questions.'
  if(form.title.trim()&&form.title.trim().length<3)return 'Use a title of at least three characters, or leave it blank.'
  if(form.correct!==''&&(!Number.isInteger(Number(form.correct))||Number(form.correct)<1||Number(form.correct)>10))return 'Correct answers can carry 1–10 marks.'
  if(form.wrong!==''&&(!Number.isInteger(Number(form.wrong))||Number(form.wrong)<0||Number(form.wrong)>10))return 'The wrong-answer deduction must be 0–10 marks.'
  return ''
}
export function quickPaperBody(form,reference,key) {
  const exact=form.method==='reference'&&form.fullPaper
  return {request_key:key,exam:form.exam,count:exact?30:Number(form.count),duration_minutes:Number(form.duration),
    subjects:exact||form.scope==='all'?null:form.scope.split(','),chapter_ids:exact?[]:form.chapters,
    selection:form.method==='reference'?(exact?'exact':'from_paper'):'topics',
    ...(form.method==='reference'?{year:reference.year,shift:reference.shift}:{}),
    level:form.level,source:form.method==='reference'?'pyq':form.source,
    question_type:exact?null:form.type||null,sets_enabled:form.sets,
    ...(form.title.trim()?{title:form.title.trim()}:{}),instructions:form.instructions,
    ...(form.correct!==''?{marks_correct:Number(form.correct)}:{}),
    ...(form.wrong!==''?{marks_wrong:Number(form.wrong)}:{})}
}
