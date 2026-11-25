#!/usr/bin/env node
// Non-destructive Meshopt -> standard GLB conversion for dense Tripo reference models.
// MIT-licensed meshoptimizer decoder is installed separately from npm at build time.
import fs from 'node:fs';
import { MeshoptDecoder } from 'meshoptimizer';

const input=process.argv[2], output=process.argv[3];
if(!input||!output||input===output) {
  console.error('Usage: node unpack_meshopt.mjs INPUT.glb OUTPUT_uncompressed.glb');
  process.exit(2);
}
const data=fs.readFileSync(input);
if(data.readUInt32LE(0)!==0x46546c67 || data.readUInt32LE(4)!==2)throw Error('Expected GLB 2.0');
let off=12, json=null, bin=null;
while(off+8<=data.length) {
  const size=data.readUInt32LE(off), type=data.readUInt32LE(off+4);
  if(off+8+size>data.length)throw Error('Bad GLB chunks');
  if(type===0x4e4f534a)json=JSON.parse(data.subarray(off+8,off+8+size).toString('utf8').trim());
  if(type===0x004e4942)bin=data.subarray(off+8,off+8+size);
  off+=8+size;
}
if(!json||!bin)throw Error('GLB needs JSON and embedded BIN chunk');
await MeshoptDecoder.ready;
const pieces=[bin], pending=[];
let len=bin.length;
function pad4(x){return (4-x%4)%4;}
let converted=0;
for(const view of json.bufferViews||[]){
  const ext=view.extensions?.EXT_meshopt_compression;
  if(!ext)continue;
  if(ext.buffer!==0)throw Error('Only GLB buffer 0 supported');
  const packed=bin.subarray(ext.byteOffset,ext.byteOffset+ext.byteLength);
  if(packed.length!==ext.byteLength)throw Error('Compressed Meshopt data outside BIN');
  const result=MeshoptDecoder.decodeGltfBuffer(ext.count,ext.byteStride,packed,ext.mode,ext.filter||'NONE');
  const padding=pad4(len);
  if(padding){pieces.push(Buffer.alloc(padding));len+=padding;}
  const decoded=Buffer.from(result);
  view.buffer=0;
  view.byteOffset=len;
  view.byteLength=decoded.length;
  view.byteStride=ext.byteStride;
  pieces.push(decoded);len+=decoded.length;
  delete view.extensions.EXT_meshopt_compression;
  if(Object.keys(view.extensions).length===0)delete view.extensions;
  converted++;
}
if(!converted){fs.copyFileSync(input,output);console.log('No meshopt views; input copied without changes');process.exit(0);}
for(const k of ['extensionsUsed','extensionsRequired']){
  if(Array.isArray(json[k])){
    json[k]=json[k].filter(x=>x!=='EXT_meshopt_compression');
    if(!json[k].length)delete json[k];
  }
}
const paddedLength=len+pad4(len);
json.buffers[0].byteLength=paddedLength;
let jbuf=Buffer.from(JSON.stringify(json));
if(pad4(jbuf.length))jbuf=Buffer.concat([jbuf,Buffer.alloc(pad4(jbuf.length),0x20)]);
const blob=Buffer.concat([...pieces,Buffer.alloc(pad4(len))],paddedLength);
const out=Buffer.alloc(12+8+jbuf.length+8+blob.length);
out.writeUInt32LE(0x46546c67,0);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);
out.writeUInt32LE(jbuf.length,12);out.writeUInt32LE(0x4e4f534a,16);jbuf.copy(out,20);
const o=20+jbuf.length;
out.writeUInt32LE(blob.length,o);out.writeUInt32LE(0x004e4942,o+4);blob.copy(out,o+8);
fs.writeFileSync(output,out);
console.log('Converted',converted,'Meshopt buffer views into standard uncompressed GLB:',output);
