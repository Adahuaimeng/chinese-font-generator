from PIL import Image, ImageDraw, ImageFont
import os
import sys

class FontGenerator:
    def __init__(self):
        # 扩展字号配置：(每行字节数, 高度)
        self.font_configs = {
            8:  (1, 8),    # 8x8:   每行1字节，8行
            10: (2, 10),   # 10x10: 每行2字节，10行
            12: (2, 12),   # 12x12: 每行2字节，12行
            14: (2, 14),   # 14x14: 每行2字节，14行
            16: (2, 16),   # 16x16: 每行2字节，16行
            20: (3, 20),   # 20x20: 每行3字节，20行
            24: (3, 24),   # 24x24: 每行3字节，24行
            28: (4, 28),   # 28x28: 每行4字节，28行
            32: (4, 32),   # 32x32: 每行4字节，32行
            36: (5, 36),   # 36x36: 每行5字节，36行
            40: (5, 40),   # 40x40: 每行5字节，40行
        }
    
    def generate(self, ttf_path, size, font_name, output_dir=None):
        """
        生成字库库文件
        
        ttf_path: 字体文件路径
        size: 字号 (8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40)
        font_name: 字体名称拼音 (FangSong, KaiTi, HeiTi, YaHei...)
        output_dir: 输出目录，默认 lib/GB2312_{size}_{font_name}/
        """
        
        if size not in self.font_configs:
            print(f"错误：不支持字号 {size}，支持: {list(self.font_configs.keys())}")
            return False
        
        bytes_per_row, height = self.font_configs[size]
        bytes_per_char = bytes_per_row * height
        
        # 生成库名: GB2312_12_FangSong
        lib_name = f"GB2312_{size}_{font_name}"
        
        # 对象名: FangSong12 (解决冲突的关键)
        obj_name = f"{font_name}{size}"
        
        if output_dir is None:
            output_dir = f"lib/{lib_name}"
        
        src_dir = f"{output_dir}/src"
        os.makedirs(src_dir, exist_ok=True)
        
        # 检查字体
        if not os.path.exists(ttf_path):
            print(f"错误：找不到字体 {ttf_path}")
            return False
        
        try:
            font = ImageFont.truetype(ttf_path, size)
            print(f"加载字体: {ttf_path}, 字号: {size}")
        except Exception as e:
            print(f"加载失败: {e}")
            return False
        
        # 生成字库数据
        print(f"生成 {lib_name}...")
        
        font_c_path = f"{src_dir}/{lib_name}_font.c"
        with open(font_c_path, 'w', encoding='utf-8') as f:
            f.write(f'// {lib_name} Font ({size}x{size})\n')
            f.write(f'// Generated from: {os.path.basename(ttf_path)}\n')
            f.write('#include <Arduino.h>\n\n')
            f.write(f'const uint8_t {lib_name.upper()}_FONT[] = {{\n')
            
            unicode_start = 0x4E00
            unicode_end = 0x9FA5
            generated = 0
            
            for unicode in range(unicode_start, unicode_end + 1):
                char = chr(unicode)
                
                # 创建图像
                img = Image.new('1', (size, size), 0)
                draw = ImageDraw.Draw(img)
                
                # 居中绘制
                bbox = draw.textbbox((0, 0), char, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (size - w) // 2
                y = (size - h) // 2 - 1
                
                draw.text((x, y), char, font=font, fill=1)
                
                # 写入点阵数据
                for row in range(height):
                    row_val = 0
                    for col in range(size):
                        if img.getpixel((col, row)):
                            row_val |= (1 << (size - 1 - col))
                    
                    # 按字节写入
                    for b in range(bytes_per_row):
                        byte_val = (row_val >> ((bytes_per_row - 1 - b) * 8)) & 0xFF
                        f.write(f'0x{byte_val:02X},')
                    
                    f.write(f' // U+{unicode:04X} {char}\n' if row == 0 else '\n')
                
                generated += 1
                if generated % 1000 == 0:
                    print(f"  进度: {generated}/20902")
            
            f.write('};\n\n')
            f.write(f'#define FONT_{lib_name.upper()}_START 0x{unicode_start:04X}\n')
            f.write(f'#define FONT_{lib_name.upper()}_END 0x{unicode_end:04X}\n')
            f.write(f'#define FONT_{lib_name.upper()}_SIZE {size}\n')
            f.write(f'#define FONT_{lib_name.upper()}_BYTES_PER_CHAR {bytes_per_char}\n')
        
        # 生成头文件
        h_path = f"{src_dir}/{lib_name}.h"
        with open(h_path, 'w', encoding='utf-8') as f:
            f.write(f'#ifndef {lib_name.upper()}_H\n')
            f.write(f'#define {lib_name.upper()}_H\n\n')
            f.write('#include <Arduino.h>\n\n')
            f.write(f'class {lib_name} {{\n')
            f.write('public:\n')
            f.write('    bool begin() { return true; }\n')
            f.write('    \n')
            f.write('    template<typename T>\n')
            f.write('    void setTFT(T* tft) {\n')
            f.write('        _tft = (void*)tft;\n')
            f.write('        _drawPixel = [](void* t, int16_t x, int16_t y, uint16_t c) {\n')
            f.write('            ((T*)t)->drawPixel(x, y, c);\n')
            f.write('        };\n')
            f.write('        _drawChar = [](void* t, int16_t x, int16_t y, unsigned char c, uint16_t color, uint16_t bg, uint8_t size) {\n')
            f.write('            ((T*)t)->drawChar(x, y, c, color, bg, size);\n')
            f.write('        };\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    // 基础功能\n')
            f.write('    void drawString(int x, int y, const char* str, uint16_t color);\n')
            f.write(f'    void drawChinese(int x, int y, const char* ch, uint16_t color);\n')
            f.write('    \n')
            f.write('    // 自动换行（从x开始，限制宽度）\n')
            f.write('    void drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight = 0);\n')
            f.write('    \n')
            f.write('    // 基于centerX水平居中（单行）\n')
            f.write('    void drawStringCenter(int y, const char* str, uint16_t color, int centerX);\n')
            f.write('    \n')
            f.write('    // 基于centerX居中+自动换行（在maxWidth范围内，每行都居中）\n')
            f.write('    void drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight = 0);\n')
            f.write('    \n')
            f.write('    // 辅助函数\n')
            f.write('    int getStringWidth(const char* str);\n')
            f.write('    int getCharWidth() { return FONT_SIZE; }\n')
            f.write('    int getCharHeight() { return FONT_SIZE; }\n')
            f.write('    \n')
            f.write('private:\n')
            f.write('    void* _tft;\n')
            f.write('    void (*_drawPixel)(void*, int16_t, int16_t, uint16_t);\n')
            f.write('    void (*_drawChar)(void*, int16_t, int16_t, unsigned char, uint16_t, uint16_t, uint8_t);\n')
            f.write(f'    static const int FONT_SIZE = {size};\n')
            f.write(f'    static const int BYTES_PER_ROW = {bytes_per_row};\n')
            f.write('};\n\n')
            f.write(f'extern {lib_name} {obj_name};\n')
            f.write(f'\n#endif // {lib_name.upper()}_H\n')
        
        # 生成cpp文件
        cpp_path = f"{src_dir}/{lib_name}.cpp"
        with open(cpp_path, 'w', encoding='utf-8') as f:
            f.write(f'#include "{lib_name}.h"\n')
            f.write(f'#include "{lib_name}_font.c"\n\n')
            f.write(f'{lib_name} {obj_name};\n\n')
            
            # drawChinese
            f.write(f'void {lib_name}::drawChinese(int x, int y, const char* ch, uint16_t color) {{\n')
            f.write('    if(!_tft) return;\n')
            f.write('    \n')
            f.write('    uint8_t c0 = ch[0];\n')
            f.write('    if(c0 < 0x80) return;\n')
            f.write('    \n')
            f.write('    uint32_t unicode;\n')
            f.write('    if((c0 & 0xF0) == 0xE0) {\n')
            f.write('        unicode = ((c0 & 0x0F) << 12) | ((ch[1] & 0x3F) << 6) | (ch[2] & 0x3F);\n')
            f.write('    } else {\n')
            f.write('        return;\n')
            f.write('    }\n')
            f.write('    \n')
            f.write(f'    if(unicode < FONT_{lib_name.upper()}_START || unicode > FONT_{lib_name.upper()}_END) return;\n')
            f.write(f'    uint32_t offset = (unicode - FONT_{lib_name.upper()}_START) * FONT_{lib_name.upper()}_BYTES_PER_CHAR;\n')
            f.write('    \n')
            f.write(f'    for(int row = 0; row < FONT_SIZE; row++) {{\n')
            f.write(f'        uint32_t rowData = 0;\n')
            f.write(f'        for(int b = 0; b < {bytes_per_row}; b++) {{\n')
            f.write(f'            rowData = (rowData << 8) | {lib_name.upper()}_FONT[offset + row * {bytes_per_row} + b];\n')
            f.write(f'        }}\n')
            f.write(f'        for(int col = 0; col < FONT_SIZE; col++) {{\n')
            f.write(f'            if(rowData & (1 << (FONT_SIZE - 1 - col))) {{\n')
            f.write(f'                _drawPixel(_tft, x + col, y + row, color);\n')
            f.write(f'            }}\n')
            f.write(f'        }}\n')
            f.write(f'    }}\n')
            f.write(f'}}\n\n')
            
            # drawString
            f.write(f'void {lib_name}::drawString(int x, int y, const char* str, uint16_t color) {{\n')
            f.write('    if(!_tft) return;\n')
            f.write('    int curX = x;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            _drawChar(_tft, curX, y, c, color, 0, 1);\n')
            f.write('            curX += 6;\n')
            f.write('            i++;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                drawChinese(curX, y, &str[i], color);\n')
            f.write('                curX += FONT_SIZE;\n')
            f.write('                i += 3;\n')
            f.write('            } else { i++; }\n')
            f.write('        } else { i++; }\n')
            f.write('    }\n')
            f.write('}\n\n')
            
            # getStringWidth（辅助函数）
            f.write(f'int {lib_name}::getStringWidth(const char* str) {{\n')
            f.write('    if(!str) return 0;\n')
            f.write('    int width = 0;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            width += 6;\n')
            f.write('            i++;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                width += FONT_SIZE;\n')
            f.write('                i += 3;\n')
            f.write('            } else { i++; }\n')
            f.write('        } else { i++; }\n')
            f.write('    }\n')
            f.write('    return width;\n')
            f.write('}\n\n')
            
            # drawStringWrap（自动换行，从x开始）
            f.write(f'void {lib_name}::drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    \n')
            f.write('    int curX = x;\n')
            f.write('    int curY = y;\n')
            f.write('    int lineWidth = 0;\n')
            f.write('    int i = 0;\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineCount = 0;\n')
            f.write('    \n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        int charWidth = 0;\n')
            f.write('        int charBytes = 0;\n')
            f.write('        \n')
            f.write('        if(c < 0x80) {\n')
            f.write('            charWidth = 6;\n')
            f.write('            charBytes = 1;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 3;\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        } else { i++; continue; }\n')
            f.write('        \n')
            f.write('        // 像素有余数直接舍去，把当前字换到下一行\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            curX = x;\n')
            f.write('            curY += lineHeight;\n')
            f.write('            lineWidth = 0;\n')
            f.write('            lineCount++;\n')
            f.write('            if(lineCount >= maxLines) break;\n')
            f.write('        }\n')
            f.write('        \n')
            f.write('        if(c < 0x80) {\n')
            f.write('            _drawChar(_tft, curX, curY, c, color, 0, 1);\n')
            f.write('        } else {\n')
            f.write('            drawChinese(curX, curY, &str[i], color);\n')
            f.write('        }\n')
            f.write('        \n')
            f.write('        curX += charWidth;\n')
            f.write('        lineWidth += charWidth;\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('}\n\n')
            
            # drawStringCenter（基于centerX居中，单行）
            f.write(f'void {lib_name}::drawStringCenter(int y, const char* str, uint16_t color, int centerX) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int strWidth = getStringWidth(str);\n')
            f.write('    int startX = centerX - strWidth / 2;\n')
            f.write('    drawString(startX, y, str, color);\n')
            f.write('}\n\n')
            
            # drawStringCenterWrap（基于centerX居中+换行，在maxWidth范围内，每行都居中）
            f.write(f'void {lib_name}::drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    \n')
            f.write('    // 第一遍：分行计算，每行在maxWidth范围内\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineStarts[maxLines];\n')
            f.write('    int lineWidths[maxLines];\n')
            f.write('    int lineCount = 0;\n')
            f.write('    \n')
            f.write('    int i = 0;\n')
            f.write('    int lineWidth = 0;\n')
            f.write('    int lineStart = 0;\n')
            f.write('    \n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        int charWidth = 0;\n')
            f.write('        int charBytes = 0;\n')
            f.write('        \n')
            f.write('        if(c < 0x80) {\n')
            f.write('            charWidth = 6;\n')
            f.write('            charBytes = 1;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 3;\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        } else { i++; continue; }\n')
            f.write('        \n')
            f.write('        // 需要换行？像素有余数直接舍去\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            lineStarts[lineCount] = lineStart;\n')
            f.write('            lineWidths[lineCount] = lineWidth;\n')
            f.write('            lineCount++;\n')
            f.write('            lineStart = i;\n')
            f.write('            lineWidth = charWidth;\n')
            f.write('        } else {\n')
            f.write('            lineWidth += charWidth;\n')
            f.write('        }\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    // 最后一行\n')
            f.write('    if(lineCount < maxLines && lineWidth > 0) {\n')
            f.write('        lineStarts[lineCount] = lineStart;\n')
            f.write('        lineWidths[lineCount] = lineWidth;\n')
            f.write('        lineCount++;\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    // 第二遍：绘制每行，每行基于centerX居中\n')
            f.write('    for(int line = 0; line < lineCount; line++) {\n')
            f.write('        int startIdx = lineStarts[line];\n')
            f.write('        int width = lineWidths[line];\n')
            f.write('        int drawX = centerX - width / 2;  // 基于centerX居中\n')
            f.write('        int drawY = y + line * lineHeight;\n')
            f.write('        \n')
            f.write('        // 绘制该行\n')
            f.write('        int idx = startIdx;\n')
            f.write('        int curX = drawX;\n')
            f.write('        int drawnWidth = 0;\n')
            f.write('        while(str[idx] && drawnWidth < width) {\n')
            f.write('            uint8_t c = str[idx];\n')
            f.write('            if(c < 0x80) {\n')
            f.write('                _drawChar(_tft, curX, drawY, c, color, 0, 1);\n')
            f.write('                curX += 6;\n')
            f.write('                drawnWidth += 6;\n')
            f.write('                idx++;\n')
            f.write('            } else if((c & 0xF0) == 0xE0) {\n')
            f.write('                if(str[idx+1] && str[idx+2]) {\n')
            f.write('                    drawChinese(curX, drawY, &str[idx], color);\n')
            f.write('                    curX += FONT_SIZE;\n')
            f.write('                    drawnWidth += FONT_SIZE;\n')
            f.write('                    idx += 3;\n')
            f.write('                } else { idx++; }\n')
            f.write('            } else { idx++; }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n')
        
        # 生成library.json
        json_path = f"{output_dir}/library.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write(f'  "name": "{lib_name}",\n')
            f.write(f'  "version": "1.0.0",\n')
            f.write(f'  "description": "{size}x{size} GB2312 Chinese Font ({font_name})",\n')
            f.write('  "frameworks": "arduino",\n')
            f.write('  "platforms": "espressif32"\n')
            f.write('}\n')
        
        # 统计
        font_size = os.path.getsize(font_c_path)
        print(f"\n✅ 生成完成: {lib_name}")
        print(f"  位置: {output_dir}")
        print(f"  字号: {size}x{size}")
        print(f"  字库: {font_size/1024:.1f} KB")
        print(f"\n使用方式:")
        print(f'  #include <{lib_name}.h>')
        print(f'  {obj_name}.setTFT(&tft);')
        print(f'  {obj_name}.drawString(10, 10, "中文", TFT_WHITE);')
        print(f'\n新增功能:')
        print(f'  {obj_name}.drawStringWrap(10, 10, "长文本", TFT_WHITE, 100, 20);')
        print(f'  {obj_name}.drawStringCenter(50, "居中", TFT_WHITE, 120);  // y=50, centerX=120')
        print(f'  {obj_name}.drawStringCenterWrap(80, "长文本居中", TFT_WHITE, 120, 100, 20);')

def main():
    gen = FontGenerator()
    
    # 命令行参数: python generate_font.py <ttf文件> <字号> <字体名>
    if len(sys.argv) >= 4:
        ttf = sys.argv[1]
        size = int(sys.argv[2])
        name = sys.argv[3]
        gen.generate(ttf, size, name)
    else:
        print("=" * 60)
        print("GB2312 中文点阵字库生成器")
        print("=" * 60)
        print("\n用法: python generate_font.py <ttf文件> <字号> <字体名>")
        print("\n支持字号: 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40")
        print("\n示例:")
        print('  python generate_font.py "C:/Windows/Fonts/simfang.ttf" 12 FangSong')
        print('  python generate_font.py "C:/Windows/Fonts/simfang.ttf" 16 FangSong')
        print('  python generate_font.py "C:/Windows/Fonts/simkai.ttf" 24 KaiTi')
        print('  python generate_font.py "C:/Windows/Fonts/simhei.ttf" 32 HeiTi')

if __name__ == "__main__":
    main()
