import os, string, hashlib, base64, re, plistlib, unicodedata
from collections import defaultdict
import sys
import xml.etree.ElementTree as ET
import codecs
from io import open
import traceback

def Start():
    HTTP.CacheTime = 0

def file2md5(filename):
    md5 = hashlib.md5()
    Log('file2md5 filename %s' % filename)
    filename = unicode(filename)
    f = open(filename, 'rb')
    tag = f.read(3)
    if tag == 'ID3':
        f.read(3)
        id3Size = f.read(4)
        ii0 = int(codecs.encode(id3Size[0], 'hex'), 16)
        ii1 = int(codecs.encode(id3Size[1], 'hex'), 16)
        ii2 = int(codecs.encode(id3Size[2], 'hex'), 16)
        ii3 = int(codecs.encode(id3Size[3], 'hex'), 16)
        size = ii0 << 21 | ii1 << 14 | ii2 << 7 | ii3
        seekpos = size+10

        #blank
        f.seek(seekpos)
        for i in range(0, 50000):
            ii0 = int(codecs.encode(f.read(1), 'hex'), 16)
            if ii0 == 255:
                ii1 = int(codecs.encode(f.read(1), 'hex'), 16)
                if (ii1 >> 5) == 7:
                    seekpos = seekpos + i
                    Log('SEEKPOS %s ' % seekpos)
                    break
    else:
        seekpos = 0
    
    f.seek(seekpos)
    chunk = f.read(163840)
    md5.update(chunk)
    f.close()
    tmp = md5.hexdigest()
    Log('filename:%s md5:%s', filename, tmp)
    return tmp


def alsong(musicmd5):
    url = 'http://lyrics.alsong.co.kr/alsongwebservice/service1.asmx'
    postData = '<?xml version="1.0" encoding="UTF-8"?>\n<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:SOAP-ENC="http://www.w3.org/2003/05/soap-encoding" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns2="ALSongWebServer/Service1Soap" xmlns:ns1="ALSongWebServer" xmlns:ns3="ALSongWebServer/Service1Soap12"><SOAP-ENV:Body><ns1:GetLyric7><ns1:encData>7c2d15b8f51ac2f3b2a37d7a445c3158455defb8a58d621eb77a3ff8ae4921318e49cefe24e515f79892a4c29c9a3e204358698c1cfe79c151c04f9561e945096ccd1d1c0a8d8f265a2f3fa7995939b21d8f663b246bbc433c7589da7e68047524b80e16f9671b6ea0faaf9d6cde1b7dbcf1b89aa8a1d67a8bbc566664342e12</ns1:encData><ns1:stQuery><ns1:strChecksum>%s</ns1:strChecksum><ns1:strVersion></ns1:strVersion><ns1:strMACAddress></ns1:strMACAddress><ns1:strIPAddress></ns1:strIPAddress></ns1:stQuery></ns1:GetLyric7></SOAP-ENV:Body></SOAP-ENV:Envelope>' % musicmd5
    headers = {'content-type': 'application/soap+xml; charset=utf-8'}
    try:
        page = HTTP.Request(url, data=postData, headers=headers)
    except Exception as e:
        Log('Exception:%s', e)
        Log(traceback.format_exc())
    Log(page.content)
    root = ET.fromstring(page.content)
    for child in root.iter():
        if child.tag.find('strLyric') != -1 :
            lyric = child.text
            if lyric is not None:
                lyric = lyric.replace('<br>', '\n')
                lyric = lyric.replace('[00:00.00]\n', '')
    return lyric



#http://mudchobo.tistory.com/443
####################################################################################################
class AlsongLyricFindAlbumAgent(Agent.Album):
    name = 'AlsongLyricFind'
    languages = [Locale.Language.NoLanguage]
    primary_provider = False
    #contributes_to = ['com.plexapp.agents.plexmusic', 'com.plexapp.agents.localmedia', 'com.plexapp.agents.lastfm', 'com.plexapp.agents.naver_music']

    def search(self, results, media, lang, manual=False, tree=None):
        results.add(SearchResult(id = 'null', score = 100))
    
    def update(self, metadata, media, lang):
        valid_keys = defaultdict(list)
        path = None

        for index, track in enumerate(media.children):
            track_key = track.guid or index
            # 2020-12-07 
            # local:// 이 붙은 건지, meta key에서 빠진건지 모르겠음.
            # 암튼 이 구조는 좋지 않음. medatata 기준으로 for를 돌리고 rating_key를 쓰는 게 좋으나 귀찮아 일단 패스.
            track_key = track_key.split('/')[-1]

            for item in track.items:
                for part in item.parts:
                    try:
                        filename = part.file
                        path = os.path.dirname(filename)
                        (file_root, fext) = os.path.splitext(filename)
            
                        path_files = {}
                        for p in os.listdir(path):
                            path_files[p.lower()] = p
                        
                        lrcfilename = filename[:-4] + '.lrc'
                        lrcfilename = lrcfilename.replace(os.path.sep, '_')
                        lrcfilename = lrcfilename.replace(':', '')
                        lyric_path = Prefs['lyric_path']
                        lrcfilename = os.path.join(lyric_path,lrcfilename)
                        
                        if not os.path.exists(lrcfilename):
                            musicmd5 = file2md5(filename)
                            lyric = alsong(musicmd5)
                            Log('Lyric %s' % lyric)
                            if lyric is not None:
                                with open(lrcfilename,'w+',encoding='utf8') as f:
                                    f.write(lyric)
                                    f.close()
                                metadata.tracks[track_key].lyrics[lrcfilename] = Proxy.LocalFile(lrcfilename, format='lrc')
                                valid_keys[track_key].append(lrcfilename)
                            else:
                                with open(os.path.join(lyric_path,'no_lyric.txt'),'a',encoding='utf8') as logfile:
                                    logfile.write(unicode(filename+'\n'))
                                    logfile.close()
                        else:
                            metadata.tracks[track_key].lyrics[lrcfilename] = Proxy.LocalFile(lrcfilename, format='lrc')
                            valid_keys[track_key].append(lrcfilename)
                    except Exception, e:
                        Log('Error %s ' %  e)
                    
        for key in metadata.tracks:
            metadata.tracks[key].lyrics.validate_keys(valid_keys[key])