import test from 'node:test'
import assert from 'node:assert/strict'
import { formatOmrId } from '../src/lib/omrIdentity.js'

test('OMR identity preserves all ten digits and uses only the permanent student ID',()=>{
  assert.equal(formatOmrId(11),'0000000011')
  assert.equal(formatOmrId('0000000011'),'0000000011')
  assert.equal(formatOmrId(9999999999),'9999999999')
  for(const invalid of [null,undefined,0,-1,1.5,'1e2','student11',10000000000]) assert.equal(formatOmrId(invalid),null)
})
