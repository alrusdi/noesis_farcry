# -*- coding: utf-8 -*-
from array import array
import sys

try:
    import noesis
    from inc_noesis import *
    import rapi
except:
    rapi = False

class XbgUtil(object):
    def __init__(self, path):
        if rapi:
            path = rapi.getInputName()
        self.data = open(path, 'rb')

    def cur_pos(self):
        return self.data.tell()

    def readByte(self, ct=1):
        return self.__reader('B', ct)

    def seek(self, ct=1):
        self.data.seek(ct, 1)

    def readUInt(self, ct=1):
        return self.__reader('I', ct)

    def readInt(self, ct=1):
        return self.__reader('i', ct)

    def readULong(self, ct=1):
        return self.__reader('L', ct)

    def readLong(self, ct=1):
        return self.__reader('l', ct)

    def readFloat(self, ct=1):
        return self.__reader('f', ct)

    def readShort(self, ct=1):
        return self.__reader('h', ct)

    def readStr(self, ct=None):
        res = ''
        i = 0
        while True:
            c = self.data.read(1)
            s = c.decode('ascii')
            res = '%s%s' % (res, s)
            i += 1

            if ct:
                if i == ct:
                    return str(res)
            elif not ord(s):
                return res
        return res

    def readStrEx(self):
        '''
        Zero terminated string with leading UInt with lenght
        '''
        self.readUInt()  # length
        return self.readStr()

    def __reader(self, mod='B', ct=1):
        f = array(mod)
        f.fromfile(self.data, ct)
        if ct == 1:
            return f[0]
        return list(f)


    def close(self):
        self.data.close()




class XbgReader(object):
    def __init__(self, path):
        self.path = path
        self.models = []
        self.__read()

    def __read(self):
        stream = XbgUtil(self.path)
        stream.seek(20)

        offset1 = stream.readUInt()
        azero = stream.readUInt()
        numChunks = stream.readUInt()
        #print 'NUM CHUNKS: %s' % numChunks
        #print stream.cur_pos()

        for i in range(0, numChunks):
            chunkName = stream.readStr(4)
            chunkNum = stream.readUInt()  # ?? mostly 1
            chunkSize = stream.readUInt()  # including 4byte name header
            nextChunk = stream.readUInt()
            subChunks = stream.readUInt()

            #print ('CHUNK: %s' % chunkName), chunkNum, chunkSize, nextChunk, subChunks
            if chunkName == 'LTMR':
                numMats = stream.readUInt()
                stream.readUInt()  # UNKNOWN
                #print '\tnum mats =', numMats

                for matidx in range(0, numMats):
                    matPath = stream.readStrEx()
                    matName = stream.readStrEx()
                    #print '\tMAT: "%s" => "%s"' % (matPath, matName)
            elif chunkName == 'LEKS':
                hasSkeleton = stream.readUInt()
                #print '\tHas skeleton:', hasSkeleton
            elif  chunkName == 'SDOL':
                lods_count = stream.readUInt()
                #print '\tFound %s LODs' % lods_count
                #print 'CURRENT POS:', stream.cur_pos()

                for j in range(0, lods_count):
                    self.__load_LOD(stream, [])

            else:
                #print '\tUnknown data chunk'
                stream.seek(chunkSize-20)

        stream.close()

    def __load_LOD(self, stream, vb_arr):
        somefloat = stream.readFloat()
        #print 'SF:', somefloat, stream.cur_pos()
        vb_cout = stream.readUInt()

        for i in range(0, vb_cout):
            vb_arr.append({
                'flag': stream.readUInt(),
                'stride': stream.readUInt(),
                'vcount': stream.readUInt(),
                'offset': stream.readUInt(),
                'verts': [],
                'faces': []
            })


        numEntries = stream.readUInt()
        for i in range(0, numEntries):
            stream.readUInt(7)

        #print 'SKIPED UNKNOWN: ', numEntries, stream.cur_pos()

        vb_size = stream.readUInt()
        #print 'VBSIZE:', vb_size

        pos = stream.cur_pos()

        if pos % 16 != 0:
            skip = 16 - int(pos % 16)
            stream.seek(skip)


        for vb in vb_arr:
            if vb['stride'] == 28:
                for vi in range(0, vb['vcount']):
                    stream.readInt(3)
                    stream.seek(22)
                continue

            for vi in range(0, vb['vcount']):
                #  Positions
                vx = stream.readShort() / 16383.5
                vy = stream.readShort() / 16383.5
                vz = stream.readShort() / 16383.5
                vw = stream.readShort() / 16383.5

                # UV
                u = stream.readShort() / 16383.5 + 1
                v = 2 - stream.readShort() / 16383.5

                u2, v2 = [0, 0]
                # UV2
                if vb['stride'] > 28:
                    u2 = stream.readInt() / 16383.5 + 1
                    v2 = 2 - stream.readInt() / 16383.5

                # BONE WEIGHTS ?
                '''
                if vb['stride'] == 40:
                    bone_idx = stream.readUInt()
                    bone_weight = stream.readUInt()
                '''
                # NORMALS
                nx = (stream.readByte()/255.0)*2 - 1
                ny = (stream.readByte()/255.0)*2 - 1
                nz = (stream.readByte()/255.0)*2 - 1
                nw = (stream.readByte()/255.0)*2 - 1

                if vb['stride'] > 28:
                    stream.seek(8)  # tangents & binormals

                vb['verts'].append({
                    'vt': [vx, vy, vz],
                    'uv': [u, v],
                    'uv2': [u2, v2],
                    'n': [nx, ny, nz, nw],
                    #'b': [bone_idx, bone_weight] if vb['stride'] == 40 else None
                })


            num_indexes = stream.readUInt()
            pos = stream.cur_pos()
            if pos % 16 != 0:
                skip = 16 - int(pos % 16)
                stream.seek(skip)
            #print 'POSIND', stream.cur_pos(), num_indexes
            for j in range(0, int(num_indexes/3)):
                vb['faces'].append([
                    stream.readShort()+1,
                    stream.readShort()+1,
                    stream.readShort()+1
                ])


        self.models.append(vb_arr)


def xbgCheckType(data):
	return 1

def get_tuple(v):
    if len(v) == 2:
        return (v[0], v[1], 0)
    else:
        return (v[0], v[1], v[2])

def xbgLoadModel(data, mdlList):
    reader = XbgReader(data)

    m = reader.models[0]
    meshes = []
    for s in m:
        idxList = []
        posList = []

        for f in s['faces']:
            idxList.extend([f[0]-1, f[2]-1, f[1]-1])

        for v in s['verts']:
            posList.append(NoeVec3((v['vt'][0], v['vt'][1], v['vt'][2])))

        mesh = NoeMesh(idxList, posList)

        for v in s['verts']:
            mesh.uvs.append(NoeVec3(get_tuple(v['uv'])))
            mesh.normals.append(NoeVec3(get_tuple(v['n'])).normalize())

        meshes.append(mesh)

    mdl = NoeModel(meshes)

    mdlList.append(mdl)

    return 1




def registerNoesisTypes():
    handle = noesis.register("FarCry 2/3 xbg", ".xbg")
    noesis.setHandlerTypeCheck(handle, xbgCheckType)
    noesis.setHandlerLoadModel(handle, xbgLoadModel)
    return 1





if __name__ ==  '__main__':
    fname = sys.argv[1]
    data = XbgReader(fname)

    for m in data.models:
        for s in m:
            for v in s['verts']:
                print('v %s %s %s' % (v['vt'][0], v['vt'][1], v['vt'][2]))

            for f in s['faces']:
                print('f %s %s %s' % (f[0], f[2], f[1]))
