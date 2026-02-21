# chinese-font-generator
常用6000字中文软字库生成
本字库生成仅包含GB2312字库内汉字（因为.py里面unicode_start = 0x4E00  unicode_end = 0x9FA5,作者弄这个库时只要GB2312里面的中文）
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
|      |--generate_font.py  (tools文件夹里放运行脚本）
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
setTFT(&tft)    绑定TFT对象                     font.setTFT(&tft);
2.绘制函数（主要功能函数）
函数                                                                      功能                              参数说明
drawString(x,y,str,color)                                                 绘制字符串                        x,y:坐标；str：字符串；color：颜色
drawChinese(x,y,ch,color)                                                 绘制单个中文字符                   ch：指向UTF-8中文字符的指针
drawStringWrap(x,y,str,color,maxWidth,lineHeight=0)                       自动换行绘制字符串                 maxWidth：最大宽度；lineHeight：行高(0=自动)
drawAscii(x,y,c,color)                                                    绘制单个ASCII字符                  c：字符
drawStringTruncated(x,y,str,color,maxWidth)                               截断绘制(超出部分不显示)            maxWidth：最大宽度
3.信息获取函数
函数                                        返回值                 说明
getSize()                                  字号（如16）            获取字体高度
getMaxCharsPerLine()                      每行最大字符数           基于240宽度计算
getCharWidth(str,&bytesConsumed)            字符宽度              返回像素宽度，可选输出字节数       

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


生成字库后使用示例
#include <TFT_eSPI.h>  // 或其他TFT库
#include <GB2312_FangSong_16.h>  // 生成的字库头文件

TFT_eSPI tft = TFT_eSPI();
// 自动生成的对象名：字体名驼峰化 + 字号
// 如：FangSong_16, KaiTi_24, HeiTi_32 等

void setup() {
    tft.init();
    tft.setRotation(0);
    tft.fillScreen(TFT_BLACK);
    
    // 1. 初始化字库（可选，begin始终返回true）
    FangSong_16.begin();
    
    // 2. 绑定TFT对象（必须！）
    FangSong_16.setTFT(&tft);
    
    // ========== 基础绘制 ==========
    
    // 绘制混合中英文字符串
    FangSong_16.drawString(10, 10, "Hello 世界", TFT_WHITE);
    
    // 绘制纯中文
    FangSong_16.drawString(10, 30, "你好中国", TFT_GREEN);
    
    // ========== 自动换行 ==========
    
    // 方式1：自动换行，行高自动（字号+4）
    FangSong_16.drawStringWrap(10, 50, "这是一段很长的中文文本，会自动换行显示", TFT_YELLOW, 100);  // maxWidth=100像素
    
    // 方式2：指定行高
    FangSong_16.drawStringWrap(10, 120, 
        "第一行\n第二行",  // 注意：不会处理\n，需要用maxWidth控制
        TFT_CYAN, 120, 20);  // 行高20像素
    
    // ========== 截断显示 ==========
    
    // 只显示能容纳的部分，超出不显示
    FangSong_16.drawStringTruncated(10, 180, "这段文字太长了会被截断", TFT_MAGENTA, 80);  // 只显示80像素宽度
    
    // ========== 获取信息 ==========
    
    int fontSize = FangSong_16.getSize();           // 返回 16
    int maxChars = FangSong_16.getMaxCharsPerLine(); // 返回 15（240/16）
    
    // 计算特定字符宽度
    int bytesUsed;
    int width = FangSong_16.getCharWidth("中", &bytesUsed); 
    // width = 16, bytesUsed = 3
    
    int asciiWidth = FangSong_16.getCharWidth("A", &bytesUsed);
    // asciiWidth = 6, bytesUsed = 1
}

void loop() {}
