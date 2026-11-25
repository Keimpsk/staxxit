/** Validate exports with the simulator's actual, unmodified parseReplay.
 * Node >=24, no npm packages. From repository root:
 * node --experimental-loader ./analysis/tests/simulator_ts_loader.mjs \
 *   analysis/tests/validate_simulator_replays.mjs \
 *   --simulator analysis/build/simulator-reference \
 *   --manifest analysis/results/simulator_replays/manifest.json \
 *   --output analysis/results/simulator_replays/validation.json
 */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'

const HERE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const REPO = path.dirname(HERE)
const args = process.argv.slice(2)
const options = {}
for (let i=0; i<args.length; i+=2) {
  assert.ok(args[i]?.startsWith('--') && args[i+1], 'Expected --option value')
  options[args[i].slice(2)] = args[i+1]
}
const simulatorOption = options.simulator??options['simulator-root']
assert.ok(simulatorOption && options.manifest, '--simulator (or --simulator-root) and --manifest are required')
const simulator = path.resolve(simulatorOption)
const manifestPath = path.resolve(options.manifest)
const outputPath = options.output ? path.resolve(options.output) : null
const loadJson = async file => JSON.parse(await readFile(file, 'utf8'))
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
const fileHash = async file => hash(await readFile(file))
const git = (...args) => execFileSync('git', ['-C', simulator, ...args], {encoding:'utf8'}).trim()
const {parseReplay, MAX_REPLAY_BYTES, MAX_REPLAY_MOVES} = await import(pathToFileURL(path.join(simulator,'lib/staxxit/record.ts')))
const {evaluateResult, phaseFor} = await import(pathToFileURL(path.join(simulator,'lib/staxxit/engine.ts')))
const positions = []
for (let q=-6;q<=6;q++) for(let r=-6;r<=6;r++) if(Math.max(Math.abs(q),Math.abs(r),Math.abs(q+r))<=6) positions.push(`${q},${r}`)
const color = n => n===0 ? 'W' : 'B'
const kinds = {p:'place',m:'move',c:'capture',s:'split',e:'exit',x:'pass'}

function expectedBoard(snapshot) {
  const board = {}
  snapshot.stacks.forEach((stack, index) => {
    if(stack!=='-') board[positions[index]] = [...stack].map(n=>color(Number(n)))
  })
  return board
}
function compareFrame(frame, snapshot, label, variant) {
  assert.deepEqual(frame.board, expectedBoard(snapshot), `${label}: ordered stacks`)
  assert.equal(frame.current, color(snapshot.side), `${label}: side to move`)
  assert.deepEqual(frame.piecesLeft, {W:snapshot.reserve[0],B:snapshot.reserve[1]}, `${label}: reserves`)
  assert.equal(frame.consecutivePasses??0, snapshot.passes, `${label}: pass streak`)
  assert.equal(frame.variant, variant, `${label}: variant`)
  assert.equal(frame.phase, phaseFor(frame), `${label}: derived phase`)
  const totals={W:frame.piecesLeft.W,B:frame.piecesLeft.B}
  for (const stack of Object.values(frame.board)) for(const stone of stack) totals[stone]++
  assert.deepEqual(totals,{W:18,B:18},`${label}: material conservation`)
  const {score}=evaluateResult(frame)
  assert.deepEqual([[score.W.stax,score.W.pieces],[score.B.stax,score.B.pieces]],snapshot.scores,`${label}: score`)
}
function expectedMove(move) {
  const result={player:color(move.side),kind:kinds[move.t]}
  assert.ok(result.kind,`Unknown research action ${move.t}`)
  if(move.t!=='x') result.to=positions[move.q]
  if(move.t!=='x'&&move.t!=='p') result.from=positions[move.p]
  if(move.t==='s') result.h1=move.k
  return result
}
function coreMove(move) {
  const {comment,...core}=move
  return core
}
const expectedResults=[
  {over:true,winner:'W',ending:'regular'},
  {over:true,winner:'B',ending:'regular'},
  {over:true,winner:'draw',ending:'regular'},
  {over:true,winner:'draw',ending:'repetition'},
  {over:true,winner:null,ending:'blocked'},
  {over:false,winner:null,ending:null},
]
const manifest=await loadJson(manifestPath)
assert.equal(manifest.schema,'staxxit.simulator_exports.v1','Unknown export manifest schema')
assert.equal(git('rev-parse','HEAD'),manifest.target_simulator.commit,'Simulator source revision differs from export target')
execFileSync('git',['-C',simulator,'diff','--exit-code','HEAD','--','lib/staxxit','docs/STAXXIT-FORMAT.md','docs/staxxit-v1.schema.json'])
assert.notEqual(manifest.complete,false,'Incomplete export manifest')
assert.ok(Array.isArray(manifest.files)&&manifest.files.length>0,'Missing files array')
const files=[]
let moves=0,frames=0
const outcomes={}
const actions={}
const variants={}
for(const entry of manifest.files) {
  const filename=entry.file??entry.path??entry.output_file
  const traceFilename=entry.trace_file??entry.source_trace
  assert.ok(filename&&traceFilename,'Missing export/trace path')
  const replayPath=path.resolve(path.dirname(manifestPath),filename)
  const tracePath=path.isAbsolute(traceFilename) ? traceFilename : path.resolve(REPO,traceFilename)
  const text=await readFile(replayPath,'utf8')
  const trace=await loadJson(tracePath)
  const raw=JSON.parse(text)
  assert.equal(await fileHash(replayPath),entry.sha256,`${filename}: export checksum`)
  assert.equal(await fileHash(tracePath),entry.source_sha256,`${filename}: trace checksum`)
  assert.ok(Buffer.byteLength(text,'utf8')<=MAX_REPLAY_BYTES,`${filename}: byte limit`)
  assert.ok(raw.moves.length<=MAX_REPLAY_MOVES,`${filename}: move limit`)
  assert.equal(raw.version,1,`${filename}: version`)
  assert.equal(raw.variant,trace.config.variant,`${filename}: variant`)
  assert.deepEqual(raw.rules,{allowPass:true,endOnTwoPasses:true,threefold:true,restartAtCenter:true},`${filename}: rules`)
  assert.deepEqual(raw.moves.map(coreMove),trace.moves.map(expectedMove),`${filename}: exact action translation`)
  const replay=parseReplay(text)
  assert.equal(replay.frames.length,trace.snapshots.length,`${filename}: frame count`)
  for(let i=0;i<replay.frames.length;i++) compareFrame(replay.frames[i],trace.snapshots[i],`${filename}, ply ${i}`,raw.variant)
  const {over,winner,ending}=replay.result
  assert.deepEqual({over,winner,ending},expectedResults[trace.outcome],`${filename}: ending/result`)
  if(trace.outcome===5) assert.equal(raw.result,undefined,`${filename}: a turn limit must remain an open replay`)
  else assert.deepEqual(raw.result,{winner,ending},`${filename}: declared result`)
  moves+=raw.moves.length;frames+=replay.frames.length
  for(const move of raw.moves) actions[move.kind]=(actions[move.kind]??0)+1
  variants[raw.variant]=(variants[raw.variant]??0)+1
  outcomes[trace.termination]=(outcomes[trace.termination]??0)+1
  files.push({file:filename,trace_file:traceFilename,variant:raw.variant,moves:raw.moves.length,
    frames:replay.frames.length,bytes:Buffer.byteLength(text,'utf8'),ending,winner,
    export_sha256:await fileHash(replayPath),trace_sha256:await fileHash(tracePath)})
}
const sourcePaths=['lib/staxxit/record.ts','lib/staxxit/engine.ts','lib/staxxit/geometry.ts','lib/staxxit/types.ts','docs/STAXXIT-FORMAT.md','docs/staxxit-v1.schema.json']
const source={}
for(const filename of sourcePaths) source[filename]={git_blob:git('rev-parse',`HEAD:${filename}`),sha256:await fileHash(path.join(simulator,filename))}
const report={status:'passed',method:'Actual simulator parseReplay and central engine, unchanged source; every archived frame compared.',
  simulator_repository:'https://github.com/Keimpsk/staxxit-simulator',simulator_branch:'feature/game-rules-and-replay',
  simulator_commit:git('rev-parse','HEAD'),node_version:process.version,source,
  files:files.length,moves,frames,outcomes,actions,variants,manifest_sha256:await fileHash(manifestPath),
  validator_sha256:await fileHash(fileURLToPath(import.meta.url)),loader_sha256:await fileHash(path.join(HERE,'tests/simulator_ts_loader.mjs')),
  records:files}
if(outputPath) {await mkdir(path.dirname(outputPath),{recursive:true});await writeFile(outputPath,JSON.stringify(report,null,2)+'\n','utf8')}
process.stdout.write(JSON.stringify({status:report.status,files:report.files,moves,frames,outcomes,simulator_commit:report.simulator_commit},null,2)+'\n')
