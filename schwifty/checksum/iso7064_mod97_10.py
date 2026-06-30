from schwifty import checksum


# Bosnia and Herzegovina (BA)
# Montenegro (ME)
# North Macedonia (MK)
# Portugal (PT)
# Serbia (RS)
# Slovenia (SI)
# East Timor (TL)
@checksum.register("BA", "ME", "MK", "PT", "RS", "SI", "TL")
class DefaultAlgorithm(checksum.ISO7064_mod97_10):
    name = "default"
