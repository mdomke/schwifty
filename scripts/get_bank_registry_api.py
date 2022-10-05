r'''
To find comprehensive list of bic/swift entries, we use some tricks:

1. generate fake ibans
2. send fake ibans to third party apis to validate the iban
3. if valid result returned, add it to the results
'''

import fire
import itertools
import json
import re
import requests
import rstr
import schwifty

from pathlib import Path


def try_iban_validate_ibancalculator(iban_str:str):
    '''
    validate the iban with https://www.ibancalculator.com/iban_validieren.html
    '''
    url = 'https://www.ibancalculator.com/iban_validieren.html'
    data = {
        'tx_valIBAN_pi1[iban]': iban_str,
        'tx_valIBAN_pi1[fi]': 'fi',
        'no_cache': '1',
        'Action': 'validate IBAN, look up BIC'
    }
    res = requests.post(
        url,
        data=data,
    )
    if res.status_code != 200:
        raise ConnectionError()
    text = res.text
    sres = re.search(r'BIC:</b> (\w+)', text)
    if sres is not None:
        bic = sres.groups()[0]
        bank_sres = re.search(r'Bank:</b> (<a[\w\s=\":/.-]+>)?([\w\s\"\'-]+)', text)
        if bank_sres == None:
            print('Unexpected')
            raise ValueError()
        bank_name = bank_sres.groups()[-1]
        return {
            'country_code': iban_str[:2],
            'primary': True,
            'bic': bic,
            'bank_code': schwifty.IBAN(iban_str).bank_code,
            'name': bank_name,
            'short_name': bank_name,
        }
    return None


def main(
    registry_path:str,
    country_code:str,
    out_dir:str,
    log_freq:int=50,
):
    with open(registry_path, 'r', encoding='utf-8') as f:
        registries = json.load(f)

    registry = registries[country_code]
    positions = registry['positions']
    pbac_s, pbac_e = positions['bank_code'][:2]
    pbrc_s, pbrc_e = positions['branch_code'][:2]
    pacc_s, pacc_e = positions['account_code'][:2]
    bic_regs = []
    ct = 0
    pattern = schwifty.registry.get('iban')[country_code]['regex'].pattern
    if pattern.startswith('^\\d{'):
        codes = '0123456789'
    elif pattern.startswith('^[A-Z]{'):
        codes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    else:
        codes = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    bban = rstr.xeger(pattern)
    branch_code = bban[pbrc_s:pbrc_e]
    account_code = bban[pacc_s:pacc_e]
    for bank_code in itertools.product(codes, repeat=pbac_e-pbac_s):
        bank_code = ''.join(bank_code)
        try:
            iban = schwifty.IBAN.generate(country_code, bank_code, account_code, branch_code)
            iban_str = iban.formatted
            bic_reg = try_iban_validate_ibancalculator(iban_str)
            if bic_reg is not None:
                bic_regs.append(bic_reg)
                print(bic_reg)
            if ct % log_freq == 0:
                print(f'current bank_code: {bank_code}')
            ct += 1
        except Exception as e:
            ...
    if len(bic_regs) > 0:
        with open(Path(out_dir) / f'generated_{country_code.lower()}.json', 'w', encoding='utf-8') as f:
            json.dump(bic_regs, f, indent=2)

if __name__ == '__main__':
    fire.Fire(main)