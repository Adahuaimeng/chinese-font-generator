from PIL import Image, ImageDraw, ImageFont
import os
import sys
import argparse

class FontGeneratorFull:
    def __init__(self):
        # 字号配置：(每行字节数, 高度)
        self.font_configs = {
            8:  (1, 8),
            10: (2, 10),
            12: (2, 12),
            14: (2, 14),
            16: (2, 16),
            20: (3, 20),
            24: (3, 24),
            28: (4, 28),
            32: (4, 32),
            36: (5, 36),
            40: (5, 40),
        }
    
    def is_valid_char(self, char, font, size):
        """检查字符是否有实际字形（非空白）"""
        # 创建图像测试
        img = Image.new('1', (size, size), 0)
        draw = ImageDraw.Draw(img)
        
        # 尝试绘制
        try:
            draw.text((0, 0), char, font=font, fill=1)
        except:
            return False
        
        # 检查是否有任何像素
        pixels = list(img.getdata())
        return sum(pixels) > 0
    
    def generate(self, ttf_path, size, font_name, output_dir=None):
        """
        生成TTF中所有有效字符的字库
        
        ttf_path: 字体文件路径
        size: 字号
        font_name: 字体名称拼音
        """
        
        if size not in self.font_configs:
            print(f"错误：不支持字号 {size}，支持: {list(self.font_configs.keys())}")
            return False
        
        bytes_per_row, height = self.font_configs[size]
        bytes_per_char = bytes_per_row * height
        
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
        
        # 扫描所有可能的Unicode字符（常用范围）
        print("扫描字体中的有效字符...")
        
        # 扫描范围：基本多文种平面(BMP)常用区域
        scan_ranges = [
            (0x0020, 0x007E),   # 基本拉丁文（ASCII可打印）
            (0x00A0, 0x00FF),   # 拉丁文补充1
            (0x0100, 0x017F),   # 拉丁文扩展A
            (0x0180, 0x024F),   # 拉丁文扩展B
            (0x0250, 0x02AF),   # 国际音标
            (0x02B0, 0x02FF),   # 占位修饰符
            (0x0300, 0x036F),   # 组合附加符号
            (0x0370, 0x03FF),   # 希腊文和科普特文
            (0x0400, 0x04FF),   # 西里尔文
            (0x2000, 0x206F),   # 常用标点
            (0x2070, 0x209F),   # 上标和下标
            (0x20A0, 0x20CF),   # 货币符号
            (0x2100, 0x214F),   # 字母式符号
            (0x2150, 0x218F),   # 数字形式
            (0x2190, 0x21FF),   # 箭头
            (0x2200, 0x22FF),   # 数学运算符
            (0x2300, 0x23FF),   # 杂项技术符号
            (0x2460, 0x24FF),   # 带圆圈或括号的字母数字
            (0x25A0, 0x25FF),   # 几何图形
            (0x2600, 0x26FF),   # 杂项符号
            (0x2700, 0x27BF),   # 装饰符号
            (0x3000, 0x303F),   # CJK符号和标点
            (0x3040, 0x309F),   # 日文平假名
            (0x30A0, 0x30FF),   # 日文片假名
            (0x3100, 0x312F),   # 注音符号
            (0x3130, 0x318F),   # 谚文兼容字母
            (0x3200, 0x32FF),   # 带圈CJK字母和月份
            (0x3300, 0x33FF),   # CJK兼容
            (0x4E00, 0x9FFF),   # CJK统一表意文字（常用汉字）
            (0xAC00, 0xD7AF),   # 谚文音节（韩文）
            (0xF900, 0xFAFF),   # CJK兼容表意文字
            (0xFF00, 0xFFEF),   # 全角ASCII、半角片假名
        ]
        
        # 收集有效字符
        valid_chars = []
        for start, end in scan_ranges:
            for unicode in range(start, end + 1):
                try:
                    char = chr(unicode)
                    if self.is_valid_char(char, font, size):
                        valid_chars.append((unicode, char))
                except:
                    continue
            
            # 进度显示
            if start == 0x4E00:  # 到汉字范围时
                print(f"  已扫描 {len(valid_chars)} 个有效字符...")
        
        char_count = len(valid_chars)
        if char_count == 0:
            print("错误：未找到有效字符")
            return False
        
        print(f"共找到 {char_count} 个有效字符")
        
        # 按Unicode排序（二分查找需要有序）
        valid_chars.sort(key=lambda x: x[0])
        
        # 库名和对象名
        lib_name = f"GB2312_{size}_{font_name}_Full"
        obj_name = f"{font_name}{size}_Full"
        
        if output_dir is None:
            output_dir = f"lib/{lib_name}"
        
        src_dir = f"{output_dir}/src"
        os.makedirs(src_dir, exist_ok=True)
        
        print(f"生成 {lib_name}...")
        
        # 生成字库数据C文件
        font_c_path = f"{src_dir}/{lib_name}_font.c"
        with open(font_c_path, 'w', encoding='utf-8') as f:
            f.write(f'// {lib_name} Full Font ({size}x{size})\n')
            f.write(f'// Generated from: {os.path.basename(ttf_path)}\n')
            f.write(f'// Total characters: {char_count}\n')
            f.write('#include <Arduino.h>\n\n')
            
            # Unicode查找表（已排序，用于二分查找）
            f.write('// Unicode查找表（已排序）\n')
            f.write(f'const uint32_t {lib_name.upper()}_UNICODE_TABLE[] = {{\n')
            for i, (unicode, char) in enumerate(valid_chars):
                f.write(f'    0x{unicode:04X},')
                if i % 8 == 7:
                    f.write('\n')
                else:
                    f.write(' ')
            if len(valid_chars) % 8 != 0:
                f.write('\n')
            f.write('};\n\n')
            
            # 字库数据
            f.write(f'const uint8_t {lib_name.upper()}_FONT[] = {{\n')
            
            for i, (unicode, char) in enumerate(valid_chars):
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
                f.write(f'    // U+{unicode:04X} {char}\n    ')
                for row in range(height):
                    row_val = 0
                    for col in range(size):
                        if img.getpixel((col, row)):
                            row_val |= (1 << (size - 1 - col))
                    
                    for b in range(bytes_per_row):
                        byte_val = (row_val >> ((bytes_per_row - 1 - b) * 8)) & 0xFF
                        f.write(f'0x{byte_val:02X},')
                f.write('\n')
                
                if (i + 1) % 100 == 0:
                    print(f"  进度: {i+1}/{char_count}")
            
            f.write('};\n\n')
            f.write(f'const int {lib_name.upper()}_CHAR_COUNT = {char_count};\n')
            f.write(f'const int {lib_name.upper()}_BYTES_PER_CHAR = {bytes_per_char};\n')
            f.write(f'const int {lib_name.upper()}_FONT_SIZE = {size};\n')
        
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
            f.write('    void drawString(int x, int y, const char* str, uint16_t color);\n')
            f.write(f'    void drawChinese(int x, int y, const char* ch, uint16_t color);\n')
            f.write('    void drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight = 0);\n')
            f.write('    void drawStringCenter(int y, const char* str, uint16_t color, int centerX);\n')
            f.write('    void drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight = 0);\n')
            f.write('    \n')
            f.write('    int getStringWidth(const char* str);\n')
            f.write('    int getCharWidth() { return FONT_SIZE; }\n')
            f.write('    int getCharHeight() { return FONT_SIZE; }\n')
            f.write('    bool hasChar(const char* ch);\n')
            f.write('    int getCharCount() { return CHAR_COUNT; }\n')
            f.write('    \n')
            f.write('private:\n')
            f.write('    int findCharIndex(const char* ch);  // 二分查找\n')
            f.write('    void* _tft;\n')
            f.write('    void (*_drawPixel)(void*, int16_t, int16_t, uint16_t);\n')
            f.write('    void (*_drawChar)(void*, int16_t, int16_t, unsigned char, uint16_t, uint16_t, uint8_t);\n')
            f.write(f'    static const int FONT_SIZE = {size};\n')
            f.write(f'    static const int BYTES_PER_ROW = {bytes_per_row};\n')
            f.write(f'    static const int CHAR_COUNT = {char_count};\n')
            f.write('};\n\n')
            f.write(f'extern {lib_name} {obj_name};\n')
            f.write(f'\n#endif // {lib_name.upper()}_H\n')
        
        # 生成cpp文件
        cpp_path = f"{src_dir}/{lib_name}.cpp"
        with open(cpp_path, 'w', encoding='utf-8') as f:
            f.write(f'#include "{lib_name}.h"\n')
            f.write(f'#include "{lib_name}_font.c"\n\n')
            f.write(f'{lib_name} {obj_name};\n\n')
            
            # 二分查找
            f.write(f'int {lib_name}::findCharIndex(const char* ch) {{\n')
            f.write('    if(!ch || !ch[0]) return -1;\n')
            f.write('    \n')
            f.write('    // 解析UTF-8获取Unicode\n')
            f.write('    uint8_t c0 = (uint8_t)ch[0];\n')
            f.write('    uint32_t unicode;\n')
            f.write('    \n')
            f.write('    if(c0 < 0x80) return -1;  // ASCII不支持（可用drawChar）\n')
            f.write('    if((c0 & 0xE0) == 0xC0) {{\n')
            f.write('        if(!ch[1]) return -1;\n')
            f.write('        unicode = ((c0 & 0x1F) << 6) | (ch[1] & 0x3F);\n')
            f.write('    }} else if((c0 & 0xF0) == 0xE0) {{\n')
            f.write('        if(!ch[1] || !ch[2]) return -1;\n')
            f.write('        unicode = ((c0 & 0x0F) << 12) | ((ch[1] & 0x3F) << 6) | (ch[2] & 0x3F);\n')
            f.write('    }} else if((c0 & 0xF8) == 0xF0) {{\n')
            f.write('        if(!ch[1] || !ch[2] || !ch[3]) return -1;\n')
            f.write('        unicode = ((c0 & 0x07) << 18) | ((ch[1] & 0x3F) << 12) | ((ch[2] & 0x3F) << 6) | (ch[3] & 0x3F);\n')
            f.write('    }} else {{\n')
            f.write('        return -1;\n')
            f.write('    }}\n')
            f.write('    \n')
            f.write('    // 二分查找\n')
            f.write('    int left = 0;\n')
            f.write('    int right = CHAR_COUNT - 1;\n')
            f.write('    while(left <= right) {{\n')
            f.write('        int mid = left + (right - left) / 2;\n')
            f.write(f'        uint32_t midUnicode = {lib_name.upper()}_UNICODE_TABLE[mid];\n')
            f.write('        if(midUnicode == unicode) return mid;\n')
            f.write('        if(midUnicode < unicode) left = mid + 1;\n')
            f.write('        else right = mid - 1;\n')
            f.write('    }}\n')
            f.write('    return -1;\n')
            f.write('}}\n\n')
            
            # hasChar
            f.write(f'bool {lib_name}::hasChar(const char* ch) {{\n')
            f.write('    return findCharIndex(ch) >= 0;\n')
            f.write('}}\n\n')
            
            # drawChinese
            f.write(f'void {lib_name}::drawChinese(int x, int y, const char* ch, uint16_t color) {{\n')
            f.write('    if(!_tft || !ch) return;\n')
            f.write('    int index = findCharIndex(ch);\n')
            f.write('    if(index < 0) return;\n')
            f.write(f'    uint32_t offset = (uint32_t)index * {lib_name.upper()}_BYTES_PER_CHAR;\n')
            f.write(f'    for(int row = 0; row < FONT_SIZE; row++) {{\n')
            f.write('        uint32_t rowData = 0;\n')
            f.write(f'        for(int b = 0; b < {bytes_per_row}; b++) {{\n')
            f.write(f'            rowData = (rowData << 8) | {lib_name.upper()}_FONT[offset + row * {bytes_per_row} + b];\n')
            f.write('        }}\n')
            f.write('        for(int col = 0; col < FONT_SIZE; col++) {\n')
            f.write('            if(rowData & (1 << (FONT_SIZE - 1 - col))) {\n')
            f.write('                _drawPixel(_tft, x + col, y + row, color);\n')
            f.write('            }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}}\n\n')
            
            # drawString
            f.write(f'void {lib_name}::drawString(int x, int y, const char* str, uint16_t color) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int curX = x;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            _drawChar(_tft, curX, y, c, color, 0, 1);\n')
            f.write('            curX += 6;\n')
            f.write('            i++;\n')
            f.write('        } else {\n')
            f.write('            int charBytes = ((c & 0xE0) == 0xC0) ? 2 : ((c & 0xF0) == 0xE0) ? 3 : ((c & 0xF8) == 0xF0) ? 4 : 1;\n')
            f.write('            if(str[i+1] && (charBytes < 2 || str[i+2]) && (charBytes < 4 || str[i+3])) {\n')
            f.write('                if(hasChar(&str[i])) {\n')
            f.write('                    drawChinese(curX, y, &str[i], color);\n')
            f.write('                    curX += FONT_SIZE;\n')
            f.write('                }\n')
            f.write('                i += charBytes;\n')
            f.write('            } else { i++; }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}}\n\n')
            
            # getStringWidth
            f.write(f'int {lib_name}::getStringWidth(const char* str) {{\n')
            f.write('    if(!str) return 0;\n')
            f.write('    int width = 0;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            width += 6;\n')
            f.write('            i++;\n')
            f.write('        } else {\n')
            f.write('            int charBytes = ((c & 0xE0) == 0xC0) ? 2 : ((c & 0xF0) == 0xE0) ? 3 : ((c & 0xF8) == 0xF0) ? 4 : 1;\n')
            f.write('            if(str[i+1] && (charBytes < 2 || str[i+2]) && (charBytes < 4 || str[i+3])) {\n')
            f.write('                if(hasChar(&str[i])) width += FONT_SIZE;\n')
            f.write('                i += charBytes;\n')
            f.write('            } else { i++; }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('    return width;\n')
            f.write('}}\n\n')
            
            # drawStringWrap
            f.write(f'void {lib_name}::drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    int curX = x, curY = y, lineWidth = 0, i = 0;\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineCount = 0;\n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        int charWidth = 0, charBytes = 0;\n')
            f.write('        bool canDraw = false;\n')
            f.write('        if(c < 0x80) { charWidth = 6; charBytes = 1; canDraw = true; }\n')
            f.write('        else {\n')
            f.write('            charBytes = ((c & 0xE0) == 0xC0) ? 2 : ((c & 0xF0) == 0xE0) ? 3 : ((c & 0xF8) == 0xF0) ? 4 : 1;\n')
            f.write('            if(str[i+1] && (charBytes < 2 || str[i+2]) && (charBytes < 4 || str[i+3])) {\n')
            f.write('                if(hasChar(&str[i])) { charWidth = FONT_SIZE; canDraw = true; }\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        }\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            curX = x; curY += lineHeight; lineWidth = 0;\n')
            f.write('            if(++lineCount >= maxLines) break;\n')
            f.write('        }\n')
            f.write('        if(canDraw) {\n')
            f.write('            if(c < 0x80) _drawChar(_tft, curX, curY, c, color, 0, 1);\n')
            f.write('            else drawChinese(curX, curY, &str[i], color);\n')
            f.write('            curX += charWidth; lineWidth += charWidth;\n')
            f.write('        }\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('}}\n\n')
            
            # drawStringCenter
            f.write(f'void {lib_name}::drawStringCenter(int y, const char* str, uint16_t color, int centerX) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int startX = centerX - getStringWidth(str) / 2;\n')
            f.write('    drawString(startX, y, str, color);\n')
            f.write('}}\n\n')
            
            # drawStringCenterWrap
            f.write(f'void {lib_name}::drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineStarts[100], lineWidths[maxLines], lineCount = 0;\n')
            f.write('    int i = 0, lineWidth = 0, lineStart = 0;\n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = str[i];\n')
            f.write('        int charWidth = 0, charBytes = 0;\n')
            f.write('        if(c < 0x80) { charWidth = 6; charBytes = 1; }\n')
            f.write('        else {\n')
            f.write('            charBytes = ((c & 0xE0) == 0xC0) ? 2 : ((c & 0xF0) == 0xE0) ? 3 : ((c & 0xF8) == 0xF0) ? 4 : 1;\n')
            f.write('            if(str[i+1] && (charBytes < 2 || str[i+2]) && (charBytes < 4 || str[i+3])) {\n')
            f.write('                if(hasChar(&str[i])) charWidth = FONT_SIZE;\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        }\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            lineStarts[lineCount] = lineStart; lineWidths[lineCount] = lineWidth;\n')
            f.write('            lineCount++; lineStart = i; lineWidth = charWidth;\n')
            f.write('        } else lineWidth += charWidth;\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('    if(lineCount < maxLines && lineWidth > 0) {\n')
            f.write('        lineStarts[lineCount] = lineStart; lineWidths[lineCount] = lineWidth; lineCount++;\n')
            f.write('    }\n')
            f.write('    for(int line = 0; line < lineCount; line++) {\n')
            f.write('        int idx = lineStarts[line], drawX = centerX - lineWidths[line] / 2;\n')
            f.write('        int drawY = y + line * lineHeight, drawnWidth = 0;\n')
            f.write('        while(str[idx] && drawnWidth < lineWidths[line]) {\n')
            f.write('            uint8_t c = str[idx];\n')
            f.write('            if(c < 0x80) {\n')
            f.write('                _drawChar(_tft, drawX, drawY, c, color, 0, 1);\n')
            f.write('                drawX += 6; drawnWidth += 6; idx++;\n')
            f.write('            } else {\n')
            f.write('                int charBytes = ((c & 0xE0) == 0xC0) ? 2 : ((c & 0xF0) == 0xE0) ? 3 : ((c & 0xF8) == 0xF0) ? 4 : 1;\n')
            f.write('                if(str[idx+1] && (charBytes < 2 || str[idx+2]) && (charBytes < 4 || str[idx+3])) {\n')
            f.write('                    if(hasChar(&str[idx])) {\n')
            f.write('                        drawChinese(drawX, drawY, &str[idx], color);\n')
            f.write('                        drawX += FONT_SIZE; drawnWidth += FONT_SIZE;\n')
            f.write('                    }\n')
            f.write('                    idx += charBytes;\n')
            f.write('                } else idx++;\n')
            f.write('            }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}}\n')
        
        # library.json
        json_path = f"{output_dir}/library.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write(f'  "name": "{lib_name}",\n')
            f.write(f'  "version": "1.0.0",\n')
            f.write(f'  "description": "{size}x{size} Full Font ({font_name}, {char_count} chars)",\n')
            f.write('  "frameworks": "arduino",\n')
            f.write('  "platforms": "espressif32"\n')
            f.write('}\n')
        
        font_size_kb = os.path.getsize(font_c_path) / 1024
        print(f"\n✅ 生成完成: {lib_name}")
        print(f"  字符数: {char_count}")
        print(f"  字库大小: {font_size_kb:.1f} KB")
        print(f"  对象名: {obj_name}")
        
        return True

def main():
    gen = FontGeneratorFull()
    
    parser = argparse.ArgumentParser(description='GB2312 全字符TTF字库生成器')
    parser.add_argument('ttf', help='字体文件路径')
    parser.add_argument('size', type=int, help='字号')
    parser.add_argument('font_name', help='字体名称拼音')
    
    args = parser.parse_args()
    
    gen.generate(args.ttf, args.size, args.font_name)

if __name__ == "__main__":
    main()
