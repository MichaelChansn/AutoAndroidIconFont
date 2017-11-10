# coding=utf-8
# !/usr/bin/env python
"""
    从icomoon中的style.css文件解析icon对应的unicode 和 color
"""
import argparse
import os
import re
import requests
import zipfile

R_ICON_NAME_PATTERN = r'\.icon-([0-9a-z_\W]+):before {'
R_ICON_CHAR_PATTERN = r'content: "\\([0-9a-f]{4})";'
R_ICON_COLOR_PATTERN = r'color: (#[0-9a-f]{3,8});'
R_ICON_STRING_DOC_HEAD = '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
R_ICON_STRING_PATTERN = '    <string name="%s">\u%s</string>\n'
R_ICON_COLOR_STRING_PATTERN = '    <color name="%s">%s</color>\n'
R_ICON_STRING_DOC_END = '</resources>'
R_ICONFONT_DESC = '''
<!-- ########################此文件自动生成，禁止修改################################## -->
<!-- ######                  此文件自动生成，禁止修改                            ###### -->
<!-- ########################此文件自动生成，禁止修改################################## -->

<!--
    iconfont key对应的unicode，必须严格遵守命名规则：
        icon的名字作为key，icon推荐使用 模块名_用途 当做命名  如：feed_tab_right_plus_icon -->
<!--
    1.生成的iconfont key是svg的文件名，生成的颜色key是svg文件名_color
    2.生成的iconfont key需要复制到各个iconfont_topic_string.xml中去
    3.生成的 color key 根据需要决定是否使用，按业务需求来（因为生成的iconfont默认是黑色，在显示的时候需要手动的设置要显示的颜色）
-->\n'''
R_ICONFONT_PATH_DESC = '<!-- %s topic 使用的ttf文件在assets中的路径，后续不可更改 -->\n'
R_ICONFONT_PATH = '<string name="%s_iconfont_path">iconfont/%s.ttf</string>\n\n\n'

MAP_ICON_NAME_TO_CHAR = {}
MAP_ICON_COLOR_TO_CHAR = {}


def readInputFile(aInputFile):
    """
        从命令行指定的style.css中解析icon 对应的unicode 和 color
    """
    with open(aInputFile) as f:
        while True:
            line = f.readline()
            if not line:
                break
            icon = re.search(R_ICON_NAME_PATTERN, line)
            if icon is not None:
                iconName = icon.group(1)
                while True:
                    line = f.readline()
                    if not line:
                        break
                    charResult = re.search(R_ICON_CHAR_PATTERN, line)
                    if charResult is not None:
                        iconChar = charResult.group(1)
                        MAP_ICON_NAME_TO_CHAR[iconName] = iconChar
                        print ("%s->%s" % (iconName, iconChar))
                        continue
                    charColor = re.search(R_ICON_COLOR_PATTERN, line)
                    if charColor is not None:
                        iconColor = charColor.group(1)
                        MAP_ICON_COLOR_TO_CHAR[iconName + '_color'] = iconColor
                        print ("%s->%s" % (iconName + '_color', iconColor))
                        continue
                    break


def writeOutputFile(aOutputFile, aTopic):
    """
        将从readInputFile解析的unicode 和 color 写入xml中
    """
    with open(aOutputFile, 'w') as f:
        f.writelines(R_ICON_STRING_DOC_HEAD)
        f.writelines(R_ICONFONT_DESC)
        f.writelines(R_ICONFONT_PATH_DESC % (aTopic))
        f.writelines(R_ICONFONT_PATH % (aTopic, aTopic))
        f.writelines('<!-- 根据svg文件名生成的iconfont对应的key -->\n')
        names = sorted(MAP_ICON_NAME_TO_CHAR.keys())
        for name in names:
            f.writelines(R_ICON_STRING_PATTERN % (name, MAP_ICON_NAME_TO_CHAR[name]))
        colors = sorted(MAP_ICON_COLOR_TO_CHAR.keys())

        f.writelines('\n\n\n<!-- 根据svg文件内的颜色生成的iconfont对应的color（如果有的话） -->\n')
        for color in colors:
            f.writelines(R_ICON_COLOR_STRING_PATTERN % (color, MAP_ICON_COLOR_TO_CHAR[color]))
        f.writelines(R_ICON_STRING_DOC_END)


def main():
    """
        实际执行的main函数
    """
    argParser = argparse.ArgumentParser(description='从icomoon.io生成的文件夹里解析对应的iconfont编码和颜色')
    argParser.add_argument('-t', '--topic',
                           help='所属topic，即当前的iconfont要应用到哪个topic，如feed')
    argParser.add_argument('-d', '--delete',
                           help='是否删除整个过程的临时文件（在temp文件夹下），0不删除，1删除，默认1删除',
                           type=int,
                           choices=[0, 1],
                           default=1)
    args = argParser.parse_args()

    # 1.参数
    inputDir = ''
    topic = ''
    isDelete = 1

    # 2.最终生成的xml文件路径，会存放到lib-iconfont下对应的res文件夹下，以iconfont_topic.xml命名
    outputFile = ''
    outputDir = 'src/main/res/values/'

    # 3.解析topic名字
    if args.topic is not None:
        topic = args.topic
        outputFile = outputDir + 'iconfont_' + topic + '.xml'
    else:
        print '必须输入iconfont所属的topic'
        exit('-1')

    if args.delete is not None:
        isDelete = args.delete

    # 4.压缩指定topic下的svg文件
    zipFilePath = zipSvgFiles(topic)

    # 5.上传zip文件到服务器转换成ttf,然后下载到本地保存
    iconfontZipFile = uploadZipFile(zipFilePath)

    # 6.解压从服务端得到的iconfont.zip
    inputDir = unZipIconfont(iconfontZipFile)

    # 8.先解析css，获取到iconfont对应的编码和颜色值
    cssFile = inputDir + "/iconfont.css"
    readInputFile(cssFile)

    # 9. 写入文件.
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    writeOutputFile(outputFile, topic)

    # 10. 复制ttf文件到 asserts文件夹下
    srcFile = inputDir + '/iconfont.ttf'
    disDir = 'src/main/assets/iconfont/'
    disFile = disDir + topic + '.ttf'
    if os.path.exists(disFile):
        os.remove(disFile)
    if not os.path.exists(disDir):
        os.makedirs(disDir)
    os.system("cp %s %s" % (srcFile, disFile))

    # 11.删除临时文件
    if isDelete == 1:
        deleteTempFiles('temp/')


def zipSvgFiles(aTopic):
    """
    将svg-icons文件夹下topic下的所有svg文件打包成一个zip文件，以topic.zip命名。
    :param aTopic: topic名
    :return: zip文件路径
    """
    zipOutputDir = 'temp/'
    if not os.path.exists(zipOutputDir):
        os.makedirs(zipOutputDir)

    zipOutputFile = zipOutputDir + aTopic + '.zip'
    if os.path.exists(zipOutputFile):
        os.remove(zipOutputFile)

    zipFile = zipfile.ZipFile(zipOutputFile, 'w', zipfile.ZIP_DEFLATED)
    sourceDir = "svg-icons/" + aTopic

    if not os.listdir(sourceDir):
        print sourceDir + '文件夹下不存在svg文件'
        exit('-1')

    for dirPath, dirNames, fileNames in os.walk(sourceDir):
        for filename in fileNames:
            if filename.endswith('.svg'):
                zipFile.write(os.path.join(dirPath, filename))
    zipFile.close()
    return zipOutputFile


def uploadZipFile(zipPath):
    """
    上传上一步压缩的zip文件到服务器转换成ttf，并生成iconfont.zip保存到本地
    :param zipPath: zip文件路径
    :return: 经过服务器转化之后下发的iconfont zip本地路径
    """
    url = "http://localhost:3000/convert"

    data = None
    files = {'file': open(zipPath, 'rb')}
    r = requests.post(url, data, files=files)

    iconfontZipDir = 'temp/'
    if not os.path.exists(iconfontZipDir):
        os.makedirs(iconfontZipDir)

    iconfontZipFile = iconfontZipDir + '/' + 'iconfont.zip'
    if os.path.exists(iconfontZipFile):
        os.remove(iconfontZipFile)

    with open(iconfontZipFile, 'wb') as code:
        code.write(r.content)

    return iconfontZipFile


def unZipIconfont(iconfontZipFile):
    """
    解压缩从server获取的iconfont.zip到临时文件夹
    :param iconfontZipFile:
    :return:
    """
    f = zipfile.ZipFile(iconfontZipFile, 'r')
    ttfFilesDir = 'temp/iconfont'
    if not os.path.exists(ttfFilesDir):
        os.makedirs(ttfFilesDir)

    for file in f.namelist():
        f.extract(file, ttfFilesDir)

    return ttfFilesDir


def deleteTempFiles(rootDir):
    """
    递归删除指定文件夹下所有内容
    :param rootDir:
    :return:
    """
    for root, dirs, files in os.walk(rootDir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


if __name__ == '__main__':
    main()
