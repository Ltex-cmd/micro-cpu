#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { OPCODES = 16, NAME_WIDTH = 16, ROM_SIZE = OPCODES * NAME_WIDTH };

static void fail(size_t line, const char *message)
{
    if (line != 0)
        fprintf(stderr, "Line %zu: %s\n", line, message);
    else
        fprintf(stderr, "%s\n", message);
    exit(EXIT_FAILURE);
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "Usage: %s input.txt output.mif\n", argv[0]);
        return EXIT_FAILURE;
    }

    FILE *input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror(argv[1]);
        return EXIT_FAILURE;
    }

    unsigned char rom[ROM_SIZE];
    memset(rom, 0x20, sizeof rom); /* Unused opcodes contain spaces. */
    unsigned seen = 0;
    size_t line_number = 0;
    char line[128];

    while (fgets(line, sizeof line, input) != NULL) {
        ++line_number;
        size_t length = strlen(line);
        if (length == sizeof line - 1 && line[length - 1] != '\n')
            fail(line_number, "Input line is too long.");
        while (length != 0 && (line[length - 1] == '\n' || line[length - 1] == '\r'))
            line[--length] = '\0';

        char *name = line;
        while (*name == ' ' || *name == '\t')
            ++name;
        if (*name == '\0' || *name == '#')
            continue;

        unsigned opcode = 0;
        for (unsigned bit = 0; bit < 4; ++bit) {
            if (*name != '0' && *name != '1')
                fail(line_number, "Opcode must contain exactly four binary digits.");
            opcode = (opcode << 1) | (unsigned)(*name++ - '0');
        }
        if (*name != ' ' && *name != '\t')
            fail(line_number, "Separate the four-bit opcode and name with whitespace.");
        while (*name == ' ' || *name == '\t')
            ++name;

        length = strlen(name);
        if (length == 0 || length > NAME_WIDTH)
            fail(line_number, "Operation name must contain 1 to 16 ASCII characters.");
        for (size_t i = 0; i < length; ++i) {
            unsigned char ch = (unsigned char)name[i];
            if (ch < 0x20 || ch > 0x7e)
                fail(line_number, "Operation name must use printable ASCII characters.");
        }
        if ((seen & (1u << opcode)) != 0)
            fail(line_number, "Duplicate opcode.");
        seen |= 1u << opcode;
        memcpy(rom + opcode * NAME_WIDTH, name, length);
    }

    if (ferror(input))
        fail(0, "Failed to read the input file.");
    if (fclose(input) != 0)
        fail(0, "Failed to close the input file.");
    if (seen == 0)
        fail(0, "Input contains no operations.");

    static const char header[] =
        "WIDTH=8;\nDEPTH=256;\nADDRESS_RADIX=HEX;\nDATA_RADIX=HEX;\n\nCONTENT BEGIN\n";
    static const char hex[] = "0123456789ABCDEF";
    /* Each address uses exactly nine bytes: AA : DD; followed by a newline. */
    char output[sizeof header - 1 + ROM_SIZE * 9 + sizeof "END;\n" - 1];
    char *next = output;
    memcpy(next, header, sizeof header - 1);
    next += sizeof header - 1;

    for (unsigned address = 0; address < ROM_SIZE; ++address) {
        unsigned byte = rom[address];
        *next++ = hex[address >> 4];
        *next++ = hex[address & 15];
        *next++ = ' ';
        *next++ = ':';
        *next++ = ' ';
        *next++ = hex[byte >> 4];
        *next++ = hex[byte & 15];
        *next++ = ';';
        *next++ = '\n';
    }
    memcpy(next, "END;\n", sizeof "END;\n" - 1);

    /* Validate the whole input before opening/truncating the output file. */
    FILE *mif = fopen(argv[2], "wb");
    if (mif == NULL) {
        perror(argv[2]);
        return EXIT_FAILURE;
    }
    if (fwrite(output, 1, sizeof output, mif) != sizeof output) {
        (void)fclose(mif);
        fail(0, "Failed to write the output file.");
    }
    if (fclose(mif) != 0)
        fail(0, "Failed to finish writing the output file.");
    return EXIT_SUCCESS;
}
