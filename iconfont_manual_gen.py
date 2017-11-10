# coding=utf-8
# !/usr/bin/env python
"""
    从icomoon中的style.css文件解析icon对应的unicode 和 color
"""
import argparse
import os
import re

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

        f.writelines('\n\n\n<!-- 根据svg文件内的颜色生成的iconfont对应的color（可选，是否要使用由业务方决定） -->\n')
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
    argParser.add_argument('-i', '--input',
                           help='输入文件夹路径，即从icomoon.io下载下来的zip文件解压之后到得到文件夹路径')
    args = argParser.parse_args()

    # 1.参数
    inputDir = ''
    topic = ''

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

    # 3.解析要解析的文件夹路径
    if args.input is not None:
        inputDir = os.path.abspath(args.input)
    else:
        print '必须输入要解析的文件夹路径，文件夹是从icomoon.io下载下来的zip文件解压之后得到'
        exit('-1')

    # 4.先解析css，获取到iconfont对应的编码和颜色值
    cssFile = inputDir + "/style.css"
    readInputFile(cssFile)

    # 5. 写入文件.
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    writeOutputFile(outputFile, topic)

    # 6. 复制ttf文件到 asserts文件夹下
    srcFile = inputDir + '/fonts/icomoon.ttf'
    disDir = 'src/main/assets/iconfont/'
    disFile = disDir + topic + '.ttf'
    if os.path.exists(disFile):
        os.remove(disFile)
    if not os.path.exists(disDir):
        os.makedirs(disDir)
    os.system("cp %s %s" % (srcFile, disFile))
    pass


if __name__ == '__main__':
    main()
