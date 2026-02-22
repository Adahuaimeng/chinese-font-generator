# chinese-font-generator for TFT_eSPI
常用6000字中文软字库生成

本字库生成仅包含GB2312字库内汉字（因为.py里面unicode_start = 0x4E00  unicode_end = 0x9FA5,作者弄这个库时只要GB2312里面的中文）
仅在ESP32-devkit上验证过，ST7789驱动的240*240屏

使用步骤

一，确认python安装

1，

#打开vs code终端，输入python --version

#应如此类似的显示：python 3.13.7（版本不论，能用就行）

#若未安装，去https://python.org下载安装

2，安装依赖库

#终端执行：pip install Pillow

#若提示权限错误：pip install Pillow --user

二，准备ttf或ttc字体文件

方法一：win系统里内置有字体文件，路径通常在 C:/windows/Fonts/

方法二：自己下载字体（ttf或ttc格式），放到自己找得到的文件夹，此处建议放在你的项目文件夹里面，在你项目文件夹根目录里面新建一个tools文件夹，在tools文件夹里新建一个fonts文件夹，将字体存放于此

三，创建运行脚本

1，创建文件

你的项目/

|---tools/Fonts/字体文件

|       |--generate_font.py  (tools文件夹里放运行脚本）

|---lib  （此处将生成可用字库）

|---src/main.cpp等你的程序代码

|---platformio.ini

四，运行字库生成脚本

1，进入你项目目录的powershell终端

2，执行生成命令

python tools/generate_font.py "字体文件路径" 12（字号） FangSong（字体名）

示例：python tools/generate_font.py "C:/Windows/Fonts/simfang.ttf" 16 FangSong

五，运行后操作

1，应看到终端成功提示，有位置，字号，字库大小等信息

2，检查生成文件

你项目目录下的lib文件夹，以刚刚的示例为例，打开lib后应可见GB2312_FangSong_16这个文件夹，里面有一个json文件，一个src文件夹，src文件夹里应生成一个.h文件，一个.cpp文件，一个.c文件

3.此时可在你的主程序中使用了

可用函数一览

1.基础设置函数

函数            说明                           示例

begin()         初始化（始终返回true）           font.begin();

setTFT(&tft)    绑定TFT对象，必须调用            font.setTFT(&tft);

2.绘制函数（主要功能函数）

函数                                                                      功能                              参数说明

drawString(x,y,str,color)                                                 绘制字符串                        x,y:坐标；str：字符串；color：颜色

drawChinese(x,y,ch,color)                                                 绘制单个中文字符                   ch：指向UTF-8中文字符的指针

drawStringWrap(x,y,str,color,maxWidth,lineHeight=0)                       自动换行绘制字符串                 maxWidth：最大宽度；lineHeight：行高(0=自动)

drawStringCenter(y,str,color,ceterX)                                      基于centerX水平居中（单行）                     

drawStringCenterWrap(y,str,color,centerX,maxWidth,lineHeight=0)           基于CenterX居中，在maxWidth范围内自动换行，每行都居中                               

3.辅助函数

函数                                        返回值                 说明

getCharWidth                                 int            返回字体宽度

getCharHeight()                              int            返回字体高度

getStringWidth(str)                          int             计算字符串像素宽度

常见问题

1.提示“python不是内部或外部命令”

解决：Python没添加到环境变量，重装Python时勾选“Add To PATH”

2.提示“No module named'PIL'”

解决：pip install Pillow

3.提示“找不到字体文件”

解决：检查路径是否正确，Windows用/或\\，不要用\

4.生成很慢？

一个ttf有两万多汉字，耐心等等

5.生成的字库文件很大

当然，作者没做压缩简化，毕竟作者当时只需要使用12号字，这个通用生成库是顺手改的，不过这一版解决了初版的栈溢出问题


void loop() {}
