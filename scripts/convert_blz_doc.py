import json
import sys


FIELD_LENGTHS = {
    'bank_code': 8,
    'feature': 1,
    'name': 58,
    'postal_code': 5,
    'place': 35,
    'short_name': 27,
    'pan': 5,
    'bic': 11,
    'check_digit_method': 2,
    'record_number': 6,
    'mod_number': 1,
    'tbd': 1,
    'successor_bank_code': 8,
}


def read_blz_file(infp):
    for line in infp:
        record = {}
        offset = 0
        for (field, length) in FIELD_LENGTHS.items():
            record[field] = line[offset:offset+length]
            offset = offset + length
        yield record


if __name__ == '__main__':
    with open(sys.argv[1], 'r', encoding='latin-1') as fp:
        fieldnames = ('bank_code', 'name', 'short_name', 'bic', 'tbd')
        cleaned = []
        for row in read_blz_file(fp):
            if not row['bank_code'].strip():
                continue

            clean_row = {k: v.strip() for (k, v) in row.items() if k in fieldnames}

            clean_row['primary'] = row['feature'] == '1'
            clean_row['country_code'] = 'DE'

            if clean_row['bic']:
                cleaned.append(clean_row)

    with open('schwifty/bank-registry.json', 'w') as fp:
        json.dump(cleaned, fp, indent=2)
