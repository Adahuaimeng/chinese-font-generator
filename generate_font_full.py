from PIL import Image, ImageDraw, ImageFont
import os
import sys
import argparse

class FontGeneratorFull:
    def __init__(self):
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
        img = Image.new('1', (size, size), 0)
        draw = ImageDraw.Draw(img)
        try:
            draw.text((0, 0), char, font=font, fill=1)
        except:
            return False
        pixels = list(img.getdata())
        return sum(pixels) > 0

    def generate(self, ttf_path, size, font_name, output_dir=None):
        if size not in self.font_configs:
            print(f"错误：不支持字号 {size}")
            return False

        bytes_per_row, height = self.font_configs[size]
        bytes_per_char = bytes_per_row * height

        if not os.path.exists(ttf_path):
            print(f"错误：找不到字体 {ttf_path}")
            return False

        try:
            font = ImageFont.truetype(ttf_path, size)
            print(f"加载字体: {ttf_path}, 字号: {size}")
        except Exception as e:
            print(f"加载失败: {e}")
            return False

        print("扫描字体中的有效字符...")

        scan_ranges = [
            (0x0020, 0x007E),   # ASCII printable
            (0x00A0, 0x00FF),
            (0x0100, 0x017F),
            (0x0180, 0x024F),
            (0x0250, 0x02AF),
            (0x02B0, 0x02FF),
            (0x0300, 0x036F),
            (0x0370, 0x03FF),
            (0x0400, 0x04FF),
            (0x2000, 0x206F),
            (0x2070, 0x209F),
            (0x20A0, 0x20CF),
            (0x2100, 0x214F),
            (0x2150, 0x218F),
            (0x2190, 0x21FF),
            (0x2200, 0x22FF),
            (0x2300, 0x23FF),
            (0x2460, 0x24FF),
            (0x25A0, 0x25FF),
            (0x2600, 0x26FF),
            (0x2700, 0x27BF),
            (0x3000, 0x303F),
            (0x3040, 0x309F),
            (0x30A0, 0x30FF),
            (0x3100, 0x312F),
            (0x3130, 0x318F),
            (0x3200, 0x32FF),
            (0x3300, 0x33FF),
            (0x4E00, 0x9FFF),
            (0xAC00, 0xD7AF),
            (0xF900, 0xFAFF),
            (0xFF00, 0xFFEF),
        ]

        valid_chars = []       # (unicode, char, width) 存储每个字符的渲染宽度
        for start, end in scan_ranges:
            for unicode in range(start, end + 1):
                try:
                    char = chr(unicode)
                    if self.is_valid_char(char, font, size):
                        # 获取实际宽度
                        img_tmp = Image.new('1', (size, size), 0)
                        draw_tmp = ImageDraw.Draw(img_tmp)
                        bbox = draw_tmp.textbbox((0, 0), char, font=font)
                        w = bbox[2] - bbox[0]
                        valid_chars.append((unicode, char, w))
                except:
                    continue
            if start == 0x4E00:
                print(f"  已扫描 {len(valid_chars)} 个有效字符...")

        char_count = len(valid_chars)
        if char_count == 0:
            print("错误：未找到有效字符")
            return False

        print(f"共找到 {char_count} 个有效字符")
        valid_chars.sort(key=lambda x: x[0])

        lib_name = f"GB2312_{size}_{font_name}_Full"
        obj_name = f"{font_name}{size}_Full"

        if output_dir is None:
            output_dir = f"lib/{lib_name}"

        src_dir = f"{output_dir}/src"
        os.makedirs(src_dir, exist_ok=True)

        print(f"生成 {lib_name}...")

        # 生成字库数据头文件（包含宽度表）
        font_data_h_path = f"{src_dir}/{lib_name}_font_data.h"
        with open(font_data_h_path, 'w', encoding='utf-8') as f:
            f.write(f'// {lib_name} Font Data ({size}x{size})\n')
            f.write(f'// Generated from: {os.path.basename(ttf_path)}\n')
            f.write(f'// Total characters: {char_count}\n')
            f.write('#pragma once\n')
            f.write('#include <stdint.h>\n\n')

            # Unicode 查找表
            f.write(f'static const uint32_t {lib_name.upper()}_UNICODE_TABLE[] = {{\n')
            for i, (unicode, char, _) in enumerate(valid_chars):
                f.write(f'    0x{unicode:04X},')
                if i % 8 == 7:
                    f.write('\n')
                else:
                    f.write(' ')
            if len(valid_chars) % 8 != 0:
                f.write('\n')
            f.write('};\n\n')

            # 宽度表（像素）
            f.write(f'static const uint8_t {lib_name.upper()}_WIDTH_TABLE[] = {{\n')
            for i, (_, _, w) in enumerate(valid_chars):
                f.write(f'    {w},')
                if i % 16 == 15:
                    f.write('\n')
                else:
                    f.write(' ')
            if len(valid_chars) % 16 != 0:
                f.write('\n')
            f.write('};\n\n')

            # 字模数据
            f.write(f'static const uint8_t {lib_name.upper()}_FONT[] = {{\n')

            for i, (unicode, char, _) in enumerate(valid_chars):
                img = Image.new('1', (size, size), 0)
                draw = ImageDraw.Draw(img)

                bbox = draw.textbbox((0, 0), char, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (size - w) // 2
                y = (size - h) // 2 - 1   # 微调

                draw.text((x, y), char, font=font, fill=1)

                f.write(f'    // U+{unicode:04X}\n    ')
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
            f.write(f'static const int {lib_name.upper()}_CHAR_COUNT = {char_count};\n')
            f.write(f'static const int {lib_name.upper()}_BYTES_PER_CHAR = {bytes_per_char};\n')
            f.write(f'static const int {lib_name.upper()}_FONT_SIZE = {size};\n')

        # 生成头文件（不变）
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
            f.write('    void drawChinese(int x, int y, const char* ch, uint16_t color);\n')
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
            f.write('    int findCharIndex(const char* ch);\n')
            f.write('    void* _tft;\n')
            f.write('    void (*_drawPixel)(void*, int16_t, int16_t, uint16_t);\n')
            f.write('    void (*_drawChar)(void*, int16_t, int16_t, unsigned char, uint16_t, uint16_t, uint8_t);\n')
            f.write(f'    static const int FONT_SIZE = {size};\n')
            f.write(f'    static const int BYTES_PER_ROW = {bytes_per_row};\n')
            f.write(f'    static const int CHAR_COUNT = {char_count};\n')
            f.write('};\n\n')
            f.write(f'extern {lib_name} {obj_name};\n')
            f.write(f'\n#endif // {lib_name.upper()}_H\n')

        # 生成 cpp 文件（使用宽度表）
        cpp_path = f"{src_dir}/{lib_name}.cpp"
        with open(cpp_path, 'w', encoding='utf-8') as f:
            f.write(f'#include "{lib_name}.h"\n')
            f.write(f'#include "{lib_name}_font_data.h"\n\n')
            f.write(f'{lib_name} {obj_name};\n\n')
            f.write(f'// 辅助：根据索引获取字符宽度\n')
            f.write(f'static inline uint8_t getCharWidthAt(int idx) {{\n')
            f.write(f'    return {lib_name.upper()}_WIDTH_TABLE[idx];\n')
            f.write('}\n\n')

            # findCharIndex（支持 ASCII 单字节）
            f.write(f'int {lib_name}::findCharIndex(const char* ch) {{\n')
            f.write('    if(!ch || !ch[0]) return -1;\n')
            f.write('    uint8_t c0 = (uint8_t)ch[0];\n')
            f.write('    uint32_t unicode;\n')
            f.write('    if(c0 < 0x80) {\n')
            f.write('        unicode = c0;\n')
            f.write('    } else if((c0 & 0xE0) == 0xC0) {\n')
            f.write('        if(!ch[1]) return -1;\n')
            f.write('        unicode = ((c0 & 0x1F) << 6) | ((uint8_t)ch[1] & 0x3F);\n')
            f.write('    } else if((c0 & 0xF0) == 0xE0) {\n')
            f.write('        if(!ch[1] || !ch[2]) return -1;\n')
            f.write('        unicode = ((c0 & 0x0F) << 12) | (((uint8_t)ch[1] & 0x3F) << 6) | ((uint8_t)ch[2] & 0x3F);\n')
            f.write('    } else if((c0 & 0xF8) == 0xF0) {\n')
            f.write('        if(!ch[1] || !ch[2] || !ch[3]) return -1;\n')
            f.write('        unicode = ((c0 & 0x07) << 18) | (((uint8_t)ch[1] & 0x3F) << 12) | (((uint8_t)ch[2] & 0x3F) << 6) | ((uint8_t)ch[3] & 0x3F);\n')
            f.write('    } else {\n')
            f.write('        return -1;\n')
            f.write('    }\n')
            f.write('    int left = 0;\n')
            f.write('    int right = CHAR_COUNT - 1;\n')
            f.write('    while(left <= right) {\n')
            f.write('        int mid = left + (right - left) / 2;\n')
            f.write(f'        uint32_t midUnicode = {lib_name.upper()}_UNICODE_TABLE[mid];\n')
            f.write('        if(midUnicode == unicode) return mid;\n')
            f.write('        if(midUnicode < unicode) left = mid + 1;\n')
            f.write('        else right = mid - 1;\n')
            f.write('    }\n')
            f.write('    return -1;\n')
            f.write('}\n\n')

            # hasChar
            f.write(f'bool {lib_name}::hasChar(const char* ch) {{\n')
            f.write('    return findCharIndex(ch) >= 0;\n')
            f.write('}\n\n')

            # drawChinese（不变，仅用于绘制，步进由外部控制）
            f.write(f'void {lib_name}::drawChinese(int x, int y, const char* ch, uint16_t color) {{\n')
            f.write('    if(!_tft || !ch) return;\n')
            f.write('    int index = findCharIndex(ch);\n')
            f.write('    if(index < 0) return;\n')
            f.write(f'    uint32_t offset = (uint32_t)index * {lib_name.upper()}_BYTES_PER_CHAR;\n')
            f.write(f'    for(int row = 0; row < FONT_SIZE; row++) {{\n')
            f.write('        uint64_t rowData = 0;\n')
            f.write(f'        for(int b = 0; b < {bytes_per_row}; b++) {{\n')
            f.write(f'            rowData = (rowData << 8) | {lib_name.upper()}_FONT[offset + row * {bytes_per_row} + b];\n')
            f.write('        }\n')
            f.write('        for(int col = 0; col < FONT_SIZE; col++) {\n')
            f.write('            if(rowData & ((uint64_t)1 << (FONT_SIZE - 1 - col))) {\n')
            f.write('                _drawPixel(_tft, x + col, y + row, color);\n')
            f.write('            }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n\n')

            # drawString（使用宽度表）
            f.write(f'void {lib_name}::drawString(int x, int y, const char* str, uint16_t color) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int curX = x;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        int charBytes = 1;\n')
            f.write('        if((c & 0x80) == 0) charBytes = 1;\n')
            f.write('        else if((c & 0xE0) == 0xC0) charBytes = 2;\n')
            f.write('        else if((c & 0xF0) == 0xE0) charBytes = 3;\n')
            f.write('        else if((c & 0xF8) == 0xF0) charBytes = 4;\n')
            f.write('        else { i++; continue; }\n')
            f.write('        bool valid = true;\n')
            f.write('        for(int j = 1; j < charBytes; j++) {\n')
            f.write('            if(!str[i + j]) { valid = false; break; }\n')
            f.write('        }\n')
            f.write('        if(!valid) break;\n')
            f.write('        int idx = findCharIndex(&str[i]);\n')
            f.write('        if(idx >= 0) {\n')
            f.write('            drawChinese(curX, y, &str[i], color);\n')
            f.write('            curX += getCharWidthAt(idx);\n')
            f.write('        }\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('}\n\n')

            # getStringWidth（使用宽度表）
            f.write(f'int {lib_name}::getStringWidth(const char* str) {{\n')
            f.write('    if(!str) return 0;\n')
            f.write('    int width = 0;\n')
            f.write('    int i = 0;\n')
            f.write('    while(str[i]) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        int charBytes = 1;\n')
            f.write('        if((c & 0x80) == 0) charBytes = 1;\n')
            f.write('        else if((c & 0xE0) == 0xC0) charBytes = 2;\n')
            f.write('        else if((c & 0xF0) == 0xE0) charBytes = 3;\n')
            f.write('        else if((c & 0xF8) == 0xF0) charBytes = 4;\n')
            f.write('        else { i++; continue; }\n')
            f.write('        bool valid = true;\n')
            f.write('        for(int j = 1; j < charBytes; j++) {\n')
            f.write('            if(!str[i + j]) { valid = false; break; }\n')
            f.write('        }\n')
            f.write('        if(!valid) break;\n')
            f.write('        int idx = findCharIndex(&str[i]);\n')
            f.write('        if(idx >= 0) width += getCharWidthAt(idx);\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('    return width;\n')
            f.write('}\n\n')

            # drawStringWrap（使用宽度表）
            f.write(f'void {lib_name}::drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    int curX = x, curY = y, lineWidth = 0, i = 0;\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineCount = 0;\n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        int charWidth = 0, charBytes = 1;\n')
            f.write('        if((c & 0x80) == 0) charBytes = 1;\n')
            f.write('        else if((c & 0xE0) == 0xC0) charBytes = 2;\n')
            f.write('        else if((c & 0xF0) == 0xE0) charBytes = 3;\n')
            f.write('        else if((c & 0xF8) == 0xF0) charBytes = 4;\n')
            f.write('        else { i++; continue; }\n')
            f.write('        bool valid = true;\n')
            f.write('        for(int j = 1; j < charBytes; j++) {\n')
            f.write('            if(!str[i + j]) { valid = false; break; }\n')
            f.write('        }\n')
            f.write('        if(!valid) break;\n')
            f.write('        int idx = findCharIndex(&str[i]);\n')
            f.write('        if(idx >= 0) charWidth = getCharWidthAt(idx);\n')
            f.write('        if(lineWidth + charWidth > maxWidth && lineWidth > 0) {\n')
            f.write('            curX = x; curY += lineHeight; lineWidth = 0;\n')
            f.write('            if(++lineCount >= maxLines) break;\n')
            f.write('        }\n')
            f.write('        if(charWidth > 0) {\n')
            f.write('            drawChinese(curX, curY, &str[i], color);\n')
            f.write('            curX += charWidth; lineWidth += charWidth;\n')
            f.write('        }\n')
            f.write('        i += charBytes;\n')
            f.write('    }\n')
            f.write('}\n\n')

            # drawStringCenter
            f.write(f'void {lib_name}::drawStringCenter(int y, const char* str, uint16_t color, int centerX) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int startX = centerX - getStringWidth(str) / 2;\n')
            f.write('    drawString(startX, y, str, color);\n')
            f.write('}\n\n')

            # drawStringCenterWrap（使用宽度表）
            f.write(f'void {lib_name}::drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight) {{\n')
            f.write('    if(!_tft || !str || maxWidth <= 0) return;\n')
            f.write('    if(lineHeight <= 0) lineHeight = FONT_SIZE + 4;\n')
            f.write('    const int maxLines = 50;\n')
            f.write('    int lineStarts[100], lineWidths[maxLines], lineCount = 0;\n')
            f.write('    int i = 0, lineWidth = 0, lineStart = 0;\n')
            f.write('    while(str[i] && lineCount < maxLines) {\n')
            f.write('        uint8_t c = (uint8_t)str[i];\n')
            f.write('        int charWidth = 0, charBytes = 1;\n')
            f.write('        if((c & 0x80) == 0) charBytes = 1;\n')
            f.write('        else if((c & 0xE0) == 0xC0) charBytes = 2;\n')
            f.write('        else if((c & 0xF0) == 0xE0) charBytes = 3;\n')
            f.write('        else if((c & 0xF8) == 0xF0) charBytes = 4;\n')
            f.write('        else { i++; continue; }\n')
            f.write('        bool valid = true;\n')
            f.write('        for(int j = 1; j < charBytes; j++) {\n')
            f.write('            if(!str[i + j]) { valid = false; break; }\n')
            f.write('        }\n')
            f.write('        if(!valid) break;\n')
            f.write('        int idx = findCharIndex(&str[i]);\n')
            f.write('        if(idx >= 0) charWidth = getCharWidthAt(idx);\n')
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
            f.write('            uint8_t c = (uint8_t)str[idx];\n')
            f.write('            int charBytes = 1;\n')
            f.write('            if((c & 0x80) == 0) charBytes = 1;\n')
            f.write('            else if((c & 0xE0) == 0xC0) charBytes = 2;\n')
            f.write('            else if((c & 0xF0) == 0xE0) charBytes = 3;\n')
            f.write('            else if((c & 0xF8) == 0xF0) charBytes = 4;\n')
            f.write('            else { idx++; continue; }\n')
            f.write('            int index = findCharIndex(&str[idx]);\n')
            f.write('            if(index >= 0) {\n')
            f.write('                drawChinese(drawX, drawY, &str[idx], color);\n')
            f.write('                drawX += getCharWidthAt(index);\n')
            f.write('                drawnWidth += getCharWidthAt(index);\n')
            f.write('            }\n')
            f.write('            idx += charBytes;\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n')

        # library.json
        json_path = f"{output_dir}/library.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write(f'  "name": "{lib_name}",\n')
            f.write(f'  "version": "1.0.0",\n')
            f.write(f'  "description": "{size}x{size} Full Font ({font_name}, {char_count} chars, variable width)",\n')
            f.write('  "frameworks": "arduino",\n')
            f.write('  "platforms": "espressif32"\n')
            f.write('}\n')

        font_size_kb = os.path.getsize(font_data_h_path) / 1024
        print(f"\n✅ 生成完成: {lib_name}")
        print(f"  字符数: {char_count}")
        print(f"  字库大小: {font_size_kb:.1f} KB")
        print(f"  对象名: {obj_name}")

        return True

def main():
    gen = FontGeneratorFull()
    parser = argparse.ArgumentParser(description='GB2312 全字符TTF字库生成器 (1.03版)')
    parser.add_argument('ttf', help='字体文件路径')
    parser.add_argument('size', type=int, help='字号')
    parser.add_argument('font_name', help='字体名称拼音')
    args = parser.parse_args()
    gen.generate(args.ttf, args.size, args.font_name)

if __name__ == "__main__":
    main()