from PIL import Image, ImageDraw, ImageFont
import os
import sys
import argparse

class FontGeneratorPartial:
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

    def utf8_to_unicode(self, ch):
        """将UTF-8字符转换为Unicode码点（本脚本未直接使用，保留供参考）"""
        bytes_data = ch.encode('utf-8')
        if len(bytes_data) == 1:
            return bytes_data[0]
        elif len(bytes_data) == 2:
            return ((bytes_data[0] & 0x1F) << 6) | (bytes_data[1] & 0x3F)
        elif len(bytes_data) == 3:
            return ((bytes_data[0] & 0x0F) << 12) | ((bytes_data[1] & 0x3F) << 6) | (bytes_data[2] & 0x3F)
        elif len(bytes_data) == 4:
            return ((bytes_data[0] & 0x07) << 18) | ((bytes_data[1] & 0x3F) << 12) | ((bytes_data[2] & 0x3F) << 6) | (bytes_data[3] & 0x3F)
        return 0

    def generate(self, ttf_path, size, font_name, chars, output_dir=None):
        if size not in self.font_configs:
            print(f"错误：不支持字号 {size}，支持: {list(self.font_configs.keys())}")
            return False

        bytes_per_row, height = self.font_configs[size]
        bytes_per_char = bytes_per_row * height

        # 解析字符列表（去重，保持顺序）
        unique_chars = []
        seen = set()
        for ch in chars:
            if ch not in seen and ord(ch) >= 0x4E00 and ord(ch) <= 0x9FA5:
                unique_chars.append(ch)
                seen.add(ch)

        char_count = len(unique_chars)
        if char_count == 0:
            print("错误：没有有效的汉字")
            return False

        print(f"将生成 {char_count} 个汉字: {''.join(unique_chars)}")

        lib_name = f"GB2312_{size}_{font_name}_Part"
        obj_name = f"{font_name}{size}_Part"

        if output_dir is None:
            output_dir = f"lib/{lib_name}"

        src_dir = f"{output_dir}/src"
        os.makedirs(src_dir, exist_ok=True)

        if not os.path.exists(ttf_path):
            print(f"错误：找不到字体 {ttf_path}")
            return False

        try:
            font = ImageFont.truetype(ttf_path, size)
            print(f"加载字体: {ttf_path}, 字号: {size}")
        except Exception as e:
            print(f"加载失败: {e}")
            return False

        print(f"生成 {lib_name}...")

        # 生成字库数据头文件（static const，避免重复定义）
        font_data_h_path = f"{src_dir}/{lib_name}_font_data.h"
        with open(font_data_h_path, 'w', encoding='utf-8') as f:
            f.write(f'// {lib_name} Partial Font ({size}x{size})\n')
            f.write(f'// Generated from: {os.path.basename(ttf_path)}\n')
            f.write(f'// Characters: {char_count}\n')
            f.write('#pragma once\n')
            f.write('#include <stdint.h>\n\n')

            # Unicode 查找表（注释仅含码点，避免拼接风险）
            f.write(f'static const uint32_t {lib_name.upper()}_UNICODE_TABLE[] = {{\n')
            for i, ch in enumerate(unique_chars):
                unicode = ord(ch)
                f.write(f'    0x{unicode:04X},  // U+{unicode:04X}\n')
            f.write('};\n\n')

            # 字模数据（注释仅含码点）
            f.write(f'static const uint8_t {lib_name.upper()}_FONT[] = {{\n')
            for i, ch in enumerate(unique_chars):
                img = Image.new('1', (size, size), 0)
                draw = ImageDraw.Draw(img)
                bbox = draw.textbbox((0, 0), ch, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (size - w) // 2
                y = (size - h) // 2 - 1
                draw.text((x, y), ch, font=font, fill=1)

                unicode = ord(ch)
                f.write(f'    // U+{unicode:04X}\n')
                for row in range(height):
                    row_val = 0
                    for col in range(size):
                        if img.getpixel((col, row)):
                            row_val |= (1 << (size - 1 - col))
                    f.write('    ')
                    for b in range(bytes_per_row):
                        byte_val = (row_val >> ((bytes_per_row - 1 - b) * 8)) & 0xFF
                        f.write(f'0x{byte_val:02X},')
                    f.write('\n')

                if (i + 1) % 10 == 0:
                    print(f"  进度: {i+1}/{char_count}")

            f.write('};\n\n')
            f.write(f'static const int {lib_name.upper()}_CHAR_COUNT = {char_count};\n')
            f.write(f'static const int {lib_name.upper()}_BYTES_PER_CHAR = {bytes_per_char};\n')
            f.write(f'static const int {lib_name.upper()}_FONT_SIZE = {size};\n')

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
            f.write('    void drawChinese(int x, int y, const char* ch, uint16_t color);\n')
            f.write('    void drawStringWrap(int x, int y, const char* str, uint16_t color, int maxWidth, int lineHeight = 0);\n')
            f.write('    void drawStringCenter(int y, const char* str, uint16_t color, int centerX);\n')
            f.write('    void drawStringCenterWrap(int y, const char* str, uint16_t color, int centerX, int maxWidth, int lineHeight = 0);\n')
            f.write('    \n')
            f.write('    int getStringWidth(const char* str);\n')
            f.write('    int getCharWidth() { return FONT_SIZE; }\n')
            f.write('    int getCharHeight() { return FONT_SIZE; }\n')
            f.write('    bool hasChar(const char* ch);\n')
            f.write('    \n')
            f.write('private:\n')
            f.write('    int findCharIndex(const char* ch);\n')
            f.write('    void* _tft;\n')
            f.write('    void (*_drawPixel)(void*, int16_t, int16_t, uint16_t);\n')
            f.write('    void (*_drawChar)(void*, int16_t, int16_t, unsigned char, uint16_t, uint16_t, uint8_t);\n')
            f.write(f'    static const int FONT_SIZE = {size};\n')
            f.write(f'    static const int BYTES_PER_ROW = {bytes_per_row};\n')
            f.write('};\n\n')
            f.write(f'extern {lib_name} {obj_name};\n')
            f.write(f'\n#endif // {lib_name.upper()}_H\n')

        # 生成 cpp 文件（不再包含 .c，而是包含数据头文件）
        cpp_path = f"{src_dir}/{lib_name}.cpp"
        with open(cpp_path, 'w', encoding='utf-8') as f:
            f.write(f'#include "{lib_name}.h"\n')
            f.write(f'#include "{lib_name}_font_data.h"\n\n')
            f.write(f'{lib_name} {obj_name};\n\n')

            # findCharIndex - 线性查找
            f.write(f'int {lib_name}::findCharIndex(const char* ch) {{\n')
            f.write('    if(!ch || !ch[0]) return -1;\n')
            f.write('    uint8_t c0 = (uint8_t)ch[0];\n')
            f.write('    uint32_t unicode;\n')
            f.write('    if(c0 < 0x80) return -1;  // 不支持ASCII\n')
            f.write('    if((c0 & 0xF0) == 0xE0 && ch[1] && ch[2]) {\n')
            f.write('        unicode = ((c0 & 0x0F) << 12) | (((uint8_t)ch[1] & 0x3F) << 6) | ((uint8_t)ch[2] & 0x3F);\n')
            f.write('    } else {\n')
            f.write('        return -1;\n')
            f.write('    }\n')
            f.write(f'    for(int i = 0; i < {lib_name.upper()}_CHAR_COUNT; i++) {{\n')
            f.write(f'        if({lib_name.upper()}_UNICODE_TABLE[i] == unicode) return i;\n')
            f.write('    }\n')
            f.write('    return -1;\n')
            f.write('}\n\n')

            # hasChar
            f.write(f'bool {lib_name}::hasChar(const char* ch) {{\n')
            f.write('    return findCharIndex(ch) >= 0;\n')
            f.write('}\n\n')

            # drawChinese（使用 uint64_t 防止大字号溢出）
            f.write(f'void {lib_name}::drawChinese(int x, int y, const char* ch, uint16_t color) {{\n')
            f.write('    if(!_tft || !ch) return;\n')
            f.write('    int index = findCharIndex(ch);\n')
            f.write('    if(index < 0) return;\n')
            f.write(f'    uint32_t offset = index * {lib_name.upper()}_BYTES_PER_CHAR;\n')
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

            # drawString（ASCII 仍用内置字体，中文用自定义点阵）
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
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                if(hasChar(&str[i])) {\n')
            f.write('                    drawChinese(curX, y, &str[i], color);\n')
            f.write('                    curX += FONT_SIZE;\n')
            f.write('                }\n')
            f.write('                i += 3;\n')
            f.write('            } else { i++; }\n')
            f.write('        } else { i++; }\n')
            f.write('    }\n')
            f.write('}\n\n')

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
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                if(hasChar(&str[i])) width += FONT_SIZE;\n')
            f.write('                i += 3;\n')
            f.write('            } else { i++; }\n')
            f.write('        } else { i++; }\n')
            f.write('    }\n')
            f.write('    return width;\n')
            f.write('}\n\n')

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
            f.write('        if(c < 0x80) {\n')
            f.write('            charWidth = 6; charBytes = 1; canDraw = true;\n')
            f.write('        } else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                if(hasChar(&str[i])) { charWidth = FONT_SIZE; canDraw = true; }\n')
            f.write('                charBytes = 3;\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        } else { i++; continue; }\n')
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
            f.write('}\n\n')

            # drawStringCenter
            f.write(f'void {lib_name}::drawStringCenter(int y, const char* str, uint16_t color, int centerX) {{\n')
            f.write('    if(!_tft || !str) return;\n')
            f.write('    int startX = centerX - getStringWidth(str) / 2;\n')
            f.write('    drawString(startX, y, str, color);\n')
            f.write('}\n\n')

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
            f.write('        else if((c & 0xF0) == 0xE0) {\n')
            f.write('            if(str[i+1] && str[i+2]) {\n')
            f.write('                if(hasChar(&str[i])) charWidth = FONT_SIZE;\n')
            f.write('                charBytes = 3;\n')
            f.write('            } else { i++; continue; }\n')
            f.write('        } else { i++; continue; }\n')
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
            f.write('            } else if((c & 0xF0) == 0xE0) {\n')
            f.write('                if(str[idx+1] && str[idx+2]) {\n')
            f.write('                    if(hasChar(&str[idx])) {\n')
            f.write('                        drawChinese(drawX, drawY, &str[idx], color);\n')
            f.write('                        drawX += FONT_SIZE; drawnWidth += FONT_SIZE;\n')
            f.write('                    }\n')
            f.write('                    idx += 3;\n')
            f.write('                } else { idx++; }\n')
            f.write('            } else { idx++; }\n')
            f.write('        }\n')
            f.write('    }\n')
            f.write('}\n')

        # library.json
        json_path = f"{output_dir}/library.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write('{\n')
            f.write(f'  "name": "{lib_name}",\n')
            f.write(f'  "version": "1.0.0",\n')
            f.write(f'  "description": "{size}x{size} GB2312 Partial Chinese Font ({font_name}, {char_count} chars)",\n')
            f.write('  "frameworks": "arduino",\n')
            f.write('  "platforms": "espressif32"\n')
            f.write('}\n')

        font_size = os.path.getsize(font_data_h_path)
        print(f"\n✅ 生成完成: {lib_name}")
        print(f"  位置: {output_dir}")
        print(f"  字号: {size}x{size}")
        print(f"  字符数: {char_count}")
        print(f"  字库: {font_size} bytes ({font_size/1024:.1f} KB)")
        print(f"\n使用方式:")
        print(f'  #include <{lib_name}.h>')
        print(f'  {obj_name}.setTFT(&tft);')
        print(f'  {obj_name}.drawString(10, 10, "中文", TFT_WHITE);')

        return True

def main():
    gen = FontGeneratorPartial()
    parser = argparse.ArgumentParser(description='GB2312 部分字字库生成器 (1.03版)')
    parser.add_argument('ttf', help='字体文件路径')
    parser.add_argument('size', type=int, help='字号 (8/10/12/14/16/20/24/28/32/36/40)')
    parser.add_argument('font_name', help='字体名称拼音 (如 FangSong)')
    parser.add_argument('--chars', required=True, help='要生成的汉字，如 "温度连接"')
    args = parser.parse_args()
    gen.generate(args.ttf, args.size, args.font_name, args.chars)

if __name__ == "__main__":
    main()