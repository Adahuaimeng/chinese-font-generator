from PIL import Image, ImageDraw, ImageFont
import os
import sys

class FontGenerator:
    def __init__(self):
        # 支持的字号配置：(每行字节数, 高度, 屏幕每行最大字数@240宽)
        self.configs = {
            8:  (1, 8,  30),   # 8x8:   每行1字节，  8行，  240/8=30字
            10: (2, 10, 24),   # 10x10: 每行2字节， 10行，  240/10=24字
            12: (2, 12, 20),   # 12x12: 每行2字节， 12行，  240/12=20字
            14: (2, 14, 17),   # 14x14: 每行2字节， 14行，  240/14=17字
            16: (2, 16, 15),   # 16x16: 每行2字节， 16行，  240/16=15字
            20: (3, 20, 12),   # 20x20: 每行3字节， 20行，  240/20=12字
            24: (3, 24, 10),   # 24x24: 每行3字节， 24行，  240/24=10字
            28: (4, 28, 8),    # 28x28: 每行4字节， 28行，  240/28=8字
            32: (4, 32, 7),    # 32x32: 每行4字节， 32行，  240/32=7字
            36: (5, 36, 6),    # 36x36: 每行5字节， 36行，  240/36=6字
            40: (5, 40, 6),    # 40x40: 每行5字节， 40行，  240/40=6字
        }
    
    def to_camel_case(self, name):
        """转驼峰命名"""
        parts = name.split('_')
        return parts[0] + ''.join(p.capitalize() for p in parts[1:])
    
    def generate(self, ttf_path, size, font_name):
        if size not in self.configs:
            print(f"错误：不支持字号 {size}")
            print(f"支持的字号: {list(self.configs.keys())}")
            return False
        
        bytes_per_row, height, max_chars_per_line = self.configs[size]
        bytes_per_char = bytes_per_row * height
        
        # 库名: GB2312_FangSong_16
        lib_name = f"GB2312_{font_name}_{size}"
        obj_name = self.to_camel_case(f"{font_name}_{size}")
        
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
        
        print(f"生成: {lib_name} ({size}x{size})...")
        
        # 生成字库C文件
        font_c = f"{src_dir}/{lib_name}_font.c"
        with open(font_c, 'w', encoding='utf-8') as f:
            f.write(f'// {lib_name} Font ({size}x{size})\n')
            f.write(f'// Generated from: {os.path.basename(ttf_path)}\n')
            f.write('#include <Arduino.h>\n\n')
            
            # 字库数据
            f.write(f'const uint8_t {lib_name.upper()}_DATA[] = {{\n')
            
            unicode_start = 0x4E00
            unicode_end = 0x9FA5
            generated = 0
            
            for unicode in range(unicode_start, unicode_end + 1):
                char = chr(unicode)
                img = Image.new('1', (size, size), 0)
                draw = ImageDraw.Draw(img)
                
                # 居中绘制
                bbox = draw.textbbox((0, 0), char, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (size - w) // 2
                y = (size - h) // 2 - 1
                draw.text((x, y), char, font=font, fill=1)
                
                # 写入点阵
                for row in range(height):
                    row_val = 0
                    for col in range(size):
                        if img.getpixel((col, row)):
                            row_val |= (1 << (size - 1 - col))
                    for b in range(bytes_per_row):
                        byte_val = (row_val >> ((bytes_per_row - 1 - b) * 8)) & 0xFF
                        f.write(f'0x{byte_val:02X},')
                    f.write('\n')
                
                generated += 1
                if generated % 2000 == 0:
                    print(f"  进度: {generated}/20902 ({100*generated//20902}%)")
            
            f.write('};\n\n')
            
            # 添加大小常量，用于边界检查
            f.write(f'const size_t {lib_name.upper()}_DATA_SIZE = sizeof({lib_name.upper()}_DATA);\n')
            f.write(f'#define {lib_name.upper()}_CHAR_COUNT 20902\n')
            f.write(f'#define {lib_name.upper()}_BYTES_PER_CHAR {bytes_per_char}\n')
            f.write(f'#define {lib_name.upper()}_MAX_CHARS_PER_LINE {max_chars_per_line}\n')
        
        # 生成头文件
        h_file = f"{src_dir}/{lib_name}.h"
        with open(h_file, 'w') as f:
            f.write(f'#ifndef {lib_name.upper()}_H\n')
            f.write(f'#define {lib_name.upper()}_H\n')
            f.write('#include <Arduino.h>\n\n')
            
            # 辅助函数声明（在头文件中内联）
            f.write('// 辅助函数：自动换行绘制（在头文件中内联实现）\n')
            f.write('template<typename FontClass>\n')
            f.write('void drawStringWrapTemplate(FontClass* font, int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight) {\n')
            f.write('    if(!str || !font) return;\n')
            f.write('    int curX = x, curY = y;\n')
            f.write('    int i = 0;\n')
            f.write('    int lineWidth = 0;\n')
            f.write('    const int maxLines = 20;\n')
            f.write('    int lineCount = 0;\n')
            f.write('    \n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        int charWidth;\n')
            f.write('        int charBytes;\n')
            f.write('        \n')
            f.write('        // 正确解析UTF-8\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            charWidth = 6;      // ASCII宽度\n')
            f.write('            charBytes = 1;\n')
            f.write('        } else if((c & 0xE0) == 0xC0) {\n')
            f.write('            charWidth = font->getSize();\n')
            f.write('            charBytes = 2;      // 2字节UTF-8\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            charWidth = font->getSize();\n')
            f.write('            charBytes = 3;      // 3字节UTF-8 (中文)\n')
            f.write('        } else if((c & 0xF8) == 0xF0) {\n')
            f.write('            charWidth = font->getSize();\n')
            f.write('            charBytes = 4;      // 4字节UTF-8\n')
            f.write('        } else {\n')
            f.write('            i++; // 非法UTF-8，跳过\n')
            f.write('            continue;\n')
            f.write('        }\n')
            f.write('        \n')
            f.write('        // 检查剩余字节是否足够\n')
            f.write('        bool bytesValid = true;\n')
            f.write('        for(int j = 1; j < charBytes; j++) {\n')
            f.write('            if(!str[i + j]) { bytesValid = false; break; }\n')
            f.write('        }\n')
            f.write('        if(!bytesValid) break;\n')
            f.write('        \n')
            f.write('        // 检查是否会超出宽度\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            // 换行\n')
            f.write('            curX = x;\n')
            f.write('            curY += lineHeight;\n')
            f.write('            lineWidth = 0;\n')
            f.write('            lineCount++;\n')
            f.write('            if(lineCount >= maxLines) break;\n')
            f.write('        }\n')
            f.write('        \n')
            f.write('        // 绘制单个字符\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            font->drawAscii(curX, curY, c, color);\n')
            f.write('        } else {\n')
            f.write('            font->drawChinese(curX, curY, &str[i], color);\n')
            f.write('        }\n')
            f.write('        \n')
            f.write('        curX += charWidth;\n')
            f.write('        lineWidth += charWidth;\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('}\n\n')
            
            # 类定义
            f.write(f'class {lib_name} {{\n')
            f.write('public:\n')
            f.write('    bool begin() { return true; }\n')
            f.write('    \n')
            f.write('    template<typename T>\n')
            f.write('    void setTFT(T* tft) {\n')
            f.write('        _tft = (void*)tft;\n')
            f.write('        _drawPixel = [](void* t, int16_t x, int16_t y, uint16_t c) { ((T*)t)->drawPixel(x, y, c); };\n')
            f.write('        _drawChar = [](void* t, int16_t x, int16_t y, unsigned char c, uint16_t color, uint16_t bg, uint8_t s) { ((T*)t)->drawChar(x, y, c, color, bg, s); };\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    void drawString(int x, int y, const char* str, uint16_t color);\n')
            f.write('    void drawChinese(int x, int y, const char* ch, uint16_t color);\n')
            f.write('    void drawAscii(int x, int y, char c, uint16_t color);\n')
            f.write('    \n')
            f.write('    // 获取字符宽度（用于计算排版）\n')
            f.write('    int getCharWidth(const char* str, int* bytesConsumed = nullptr) {\n')
            f.write('        if(!str || !str[0]) return 0;\n')
            f.write('        uint8_t c = (uint8_t)str[0];\n')
            f.write('        if(c < 0x80) {\n')
            f.write('            if(bytesConsumed) *bytesConsumed = 1;\n')
            f.write('            return 6;  // ASCII\n')
            f.write('        }\n')
            f.write('        // 检查有效的UTF-8起始字节\n')
            f.write('        if((c & 0xE0) == 0xC0) { if(bytesConsumed) *bytesConsumed = 2; }\n')
            f.write('        else if((c & 0xF0) == 0xE0) { if(bytesConsumed) *bytesConsumed = 3; }\n')
            f.write('        else if((c & 0xF8) == 0xF0) { if(bytesConsumed) *bytesConsumed = 4; }\n')
            f.write('        else { if(bytesConsumed) *bytesConsumed = 1; }\n')
            f.write('        return FONT_SIZE;  // 中文或其他UTF-8字符\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    int getSize() { return FONT_SIZE; }\n')
            f.write('    int getMaxCharsPerLine() { return MAX_CHARS_PER_LINE; }\n')
            f.write('    \n')
            f.write('    // 自动换行绘制（限定宽度）- 修复版\n')
            f.write('    void drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight = 0) {\n')
            f.write('        if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('        if(lineHeight == 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('        \n')
            f.write('        int curX = x, curY = y;\n')
            f.write('        int i = 0;\n')
            f.write('        int lineWidth = 0;\n')
            f.write('        const int maxLines = 20;\n')
            f.write('        int lineCount = 0;\n')
            f.write('        \n')
            f.write('        while(str[i] && lineCount < maxLines) {\n')
            f.write('            uint8_t c = (uint8_t)str[i];\n')
            f.write('            int charWidth;\n')
            f.write('            int charBytes;\n')
            f.write('            \n')
            f.write('            // 正确解析UTF-8\n')
            f.write('            if(c < 0x80) {\n')
            f.write('                charWidth = 6;      // ASCII宽度\n')
            f.write('                charBytes = 1;\n')
            f.write('            } else if((c & 0xE0) == 0xC0) {\n')
            f.write('                charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 2;      // 2字节UTF-8\n')
            f.write('            } else if((c & 0xF0) == 0xE0) {\n')
            f.write('                charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 3;      // 3字节UTF-8 (中文)\n')
            f.write('            } else if((c & 0xF8) == 0xF0) {\n')
            f.write('                charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 4;      // 4字节UTF-8\n')
            f.write('            } else {\n')
            f.write('                i++; // 非法UTF-8，跳过\n')
            f.write('                continue;\n')
            f.write('            }\n')
            f.write('            \n')
            f.write('            // 检查剩余字节是否足够（防止越界读取）\n')
            f.write('            bool bytesValid = true;\n')
            f.write('            for(int j = 1; j < charBytes; j++) {\n')
            f.write('                if(!str[i + j]) { bytesValid = false; break; }\n')
            f.write('            }\n')
            f.write('            if(!bytesValid) break;\n')
            f.write('            \n')
            f.write('            // 检查是否会超出宽度，需要换行\n')
            f.write('            if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('                curX = x;\n')
            f.write('                curY += lineHeight;\n')
            f.write('                lineWidth = 0;\n')
            f.write('                lineCount++;\n')
            f.write('                if(lineCount >= maxLines) break;\n')
            f.write('            }\n')
            f.write('            \n')
            f.write('            // 绘制单个字符\n')
            f.write('            if(c < 0x80) {\n')
            f.write('                _drawChar(_tft, curX, curY, c, color, 0, 1);\n')
            f.write('            } else {\n')
            f.write('                drawChinese(curX, curY, &str[i], color);\n')
            f.write('            }\n')
            f.write('            \n')
            f.write('            curX += charWidth;\n')
            f.write('            lineWidth += charWidth;\n')
            f.write('            i += charBytes;\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('    // 截断绘制（只显示能显示的部分）- 修复版\n')
            f.write('    void drawStringTruncated(int x, int y, const char* str, uint16_t color, int maxWidth) {\n')
            f.write('        if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('        \n')
            f.write('        int curX = x;\n')
            f.write('        int i = 0;\n')
            f.write('        int totalWidth = 0;\n')
            f.write('        const int maxChars = 100;  // 安全限制\n')
            f.write('        int charCount = 0;\n')
            f.write('        \n')
            f.write('        while(str[i] && charCount < maxChars) {\n')
            f.write('            int charBytes;\n')
            f.write('            int charWidth = getCharWidth(&str[i], &charBytes);\n')
            f.write('            \n')
            f.write('            if(charWidth == 0) break;\n')
            f.write('            \n')
            f.write('            // 检查是否会超出宽度\n')
            f.write('            if(totalWidth + charWidth > maxWidth) break;\n')
            f.write('            \n')
            f.write('            // 检查UTF-8完整性\n')
            f.write('            bool bytesValid = true;\n')
            f.write('            for(int j = 1; j < charBytes; j++) {\n')
            f.write('                if(!str[i + j]) { bytesValid = false; break; }\n')
            f.write('            }\n')
            f.write('            if(!bytesValid) break;\n')
            f.write('            \n')
            f.write('            // 绘制字符\n')
            f.write('            uint8_t c = (uint8_t)str[i];\n')
            f.write('            if(c < 0x80) {\n')
            f.write('                _drawChar(_tft, curX, y, c, color, 0, 1);\n')
            f.write('            } else {\n')
            f.write('                drawChinese(curX, y, &str[i], color);\n')
            f.write('            }\n')
            f.write('            \n')
            f.write('            curX += charWidth;\n')
            f.write('            totalWidth += charWidth;\n')
            f.write('            i += charBytes;\n')
            f.write('            charCount++;\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('    \n')
            f.write('private:\n')
            f.write('    void* _tft;\n')
            f.write('    void (*_drawPixel)(void*, int16_t, int16_t, uint16_t);\n')
            f.write('    void (*_drawChar)(void*, int16_t, int16_t, unsigned char, uint16_t, uint16_t, uint8_t);\n')
            f.write(f'    static const int FONT_SIZE = {size};\n')
            f.write(f'    static const int BYTES_PER_ROW = {bytes_per_row};\n')
            f.write(f'    static const int MAX_CHARS_PER_LINE = {max_chars_per_line};\n')
            f.write('};\n\n')
            f.write(f'extern {lib_name} {obj_name};\n')
            f.write(f'#endif\n')
        
        # 生成cpp文件（带边界检查）
        cpp_file = f"{src_dir}/{lib_name}.cpp"
        with open(cpp_file, 'w') as f:
            f.write(f'#include "{lib_name}.h"\n')
            f.write(f'extern const uint8_t {lib_name.upper()}_DATA[];\n')
            f.write(f'extern const size_t {lib_name.upper()}_DATA_SIZE;\n')
            f.write(f'{lib_name} {obj_name};\n\n')
            
            # drawChinese（带边界检查）
            f.write(f'void {lib_name}::drawChinese(int x, int y, const char* ch, uint16_t color) {{\n')
            f.write('    if(!_tft || !ch) return;\n')
            f.write('    \n')
            f.write('    // 检查UTF-8有效性 (3字节中文)\n')
            f.write('    uint8_t c0 = (uint8_t)ch[0];\n')
            f.write('    if(c0 < 0x80) return;  // 不是中文\n')
            f.write('    if((c0 & 0xF0) != 0xE0) return;  // 不是3字节UTF-8\n')
            f.write('    if(!ch[1] || !ch[2]) return;  // 字节不完整\n')
            f.write('    \n')
            f.write('    // 验证后续字节是有效的UTF-8延续字节 (10xxxxxx)\n')
            f.write('    if(((uint8_t)ch[1] & 0xC0) != 0x80) return;\n')
            f.write('    if(((uint8_t)ch[2] & 0xC0) != 0x80) return;\n')
            f.write('    \n')
            f.write('    // 解码Unicode\n')
            f.write('    uint32_t unicode = ((c0 & 0x0F) << 12) | (((uint8_t)ch[1] & 0x3F) << 6) | ((uint8_t)ch[2] & 0x3F);\n')
            f.write(f'    if(unicode < 0x4E00 || unicode > 0x9FA5) return;\n')
            f.write('    \n')
            f.write('    // 计算偏移\n')
            f.write('    uint32_t charIndex = unicode - 0x4E00;\n')
            f.write(f'    uint32_t offset = charIndex * {bytes_per_char};\n')
            f.write('    \n')
            f.write('    // 边界检查\n')
            f.write(f'    uint32_t maxOffset = 20902 * {bytes_per_char};\n')
            f.write('    if(offset >= maxOffset) return;\n')
            f.write('    \n')
            f.write(f'    for(int row = 0; row < FONT_SIZE; row++) {{\n')
            f.write('        uint32_t rowData = 0;\n')
            f.write(f'        for(int b = 0; b < BYTES_PER_ROW; b++) {{\n')
            f.write('            uint32_t byteOffset = offset + row * BYTES_PER_ROW + b;\n')
            f.write('            if(byteOffset >= maxOffset) return;\n')
            f.write(f'            rowData = (rowData << 8) | {lib_name.upper()}_DATA[byteOffset];\n')
            f.write('        }\n')
            f.write('        for(int col = 0; col < FONT_SIZE; col++) {\n')
            f.write('            if(rowData & (1 << (FONT_SIZE - 1 - col)))\n')
            f.write('                _drawPixel(_tft, x + col, y + row, color);\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n\n')
            
            # drawAscii（简单封装）
            f.write(f'void {lib_name}::drawAscii(int x, int y, char c, uint16_t color) {{\n')
            f.write('    if(!_tft) return;\n')
            f.write('    _drawChar(_tft, x, y, c, color, 0, 1);\n')
            f.write('}\n\n')
            
            # drawString（带长度限制和UTF-8正确处理）
            f.write(f'void {lib_name}::drawString(int x, int y, const char* str, uint16_t color) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int curX = x, i = 0;\n')
            f.write('    const int maxChars = 100;  // 最多100个字符，防止无限循环\n')
            f.write('    int charCount = 0;\n')
            f.write('    \n')
            f.write('    while(str[i] && charCount < maxChars) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        \n')
            f.write('        if(c < 0x80) {\n')
            f.write('            // ASCII字符\n')
            f.write('            _drawChar(_tft, curX, y, c, color, 0, 1);\n')
            f.write('            curX += 6;\n')
            f.write('            i++;\n')
            f.write('            charCount++;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            // 3字节UTF-8 (中文)\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                // 验证延续字节\n')
            f.write('                if(((uint8_t)str[i+1] & 0xC0) == 0x80 && ((uint8_t)str[i+2] & 0xC0) == 0x80) {\n')
            f.write('                    drawChinese(curX, y, &str[i], color);\n')
            f.write('                    curX += FONT_SIZE;\n')
            f.write('                    i += 3;\n')
            f.write('                    charCount++;\n')
            f.write('                } else {\n')
            f.write('                    i++; // 无效的UTF-8，跳过\n')
            f.write('                }\n')
            f.write('            } else {\n')
            f.write('                break; // 不完整的UTF-8序列\n')
            f.write('            }\n')
            f.write('        } else if((c & 0xE0) == 0xC0) {\n')
            f.write('            // 2字节UTF-8 (拉丁文等)\n')
            f.write('            if(str[i+1] && ((uint8_t)str[i+1] & 0xC0) == 0x80) {\n')
            f.write('                // 对于2字节UTF-8，用方块代替或跳过\n')
            f.write('                // 这里简单处理：画一个空格宽度\n')
            f.write('                curX += FONT_SIZE;\n')
            f.write('                i += 2;\n')
            f.write('                charCount++;\n')
            f.write('            } else {\n')
            f.write('                i++;\n')
            f.write('            }\n')
            f.write('        } else if((c & 0xF8) == 0xF0) {\n')
            f.write('            // 4字节UTF-8 (emoji等)\n')
            f.write('            if(str[i+1] && str[i+2] && str[i+3]) {\n')
            f.write('                curX += FONT_SIZE;\n')
            f.write('                i += 4;\n')
            f.write('                charCount++;\n')
            f.write('            } else {\n')
            f.write('                break;\n')
            f.write('            }\n')
            f.write('        } else {\n')
            f.write('            // 非法字节，跳过\n')
            f.write('            i++;\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n')
        
        # library.json
        json_file = f"{output_dir}/library.json"
        with open(json_file, 'w') as f:
            f.write('{\n')
            f.write(f'  "name": "{lib_name}",\n')
            f.write(f'  "version": "1.0.0",\n')
            f.write(f'  "description": "{size}x{size} GB2312 Chinese Font ({font_name})",\n')
            f.write('  "frameworks": "arduino",\n')
            f.write('  "platforms": "espressif32"\n')
            f.write('}\n')
        
        # 统计
        font_c_size = os.path.getsize(font_c)
        print(f"\n✅ 生成完成: {lib_name}")
        print(f"  对象名: {obj_name}")
        print(f"  字号: {size}x{size}")
        print(f"  每行最大字数: {max_chars_per_line}")
        print(f"  字库大小: {font_c_size/1024:.1f} KB")
        print(f"\n使用方式:")
        print(f'  #include <{lib_name}.h>')
        print(f'  {obj_name}.setTFT(&tft);')
        print(f'  {obj_name}.drawString(10, 10, "中文", TFT_WHITE);')
        print(f'  {obj_name}.drawStringWrap(10, 10, "很长很长的文字", TFT_WHITE, 240);  // 自动换行')
        print(f'  {obj_name}.drawStringTruncated(10, 10, "很长很长的文字", TFT_WHITE, 100);  // 截断显示')
        
        return True

def main():
    gen = FontGenerator()
    
    if len(sys.argv) >= 4:
        gen.generate(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    else:
        print("=" * 60)
        print("GB2312 中文点阵字库生成器")
        print("=" * 60)
        print("\n用法:")
        print("  python generate_font.py <字体文件> <字号> <字体名>")
        print("\n字号支持: 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40")
        print("\n示例:")
        print('  python generate_font.py "C:/Windows/Fonts/simfang.ttf" 12 FangSong')
        print('  python generate_font.py "C:/Windows/Fonts/simfang.ttf" 14 FangSong')
        print('  python generate_font.py "C:/Windows/Fonts/simfang.ttf" 20 FangSong')
        print('  python generate_font.py "C:/Windows/Fonts/simkai.ttf" 24 KaiTi')
        print('  python generate_font.py "C:/Windows/Fonts/simhei.ttf" 28 HeiTi')
        print('  python generate_font.py "C:/Windows/Fonts/msyh.ttc" 32 YaHei')

if __name__ == "__main__":
    main()
