from pathlib import Path
from construct import Struct, Const, Rebuild, this, len_
from construct import Int32ul as UInt32, Int16ul as UInt16, Int8ul as UInt8
import csv
import numpy as np
import sys
import os
from PIL import Image

dir = os.path.dirname(os.path.realpath(__file__))
if dir not in sys.path:
	sys.path.append(dir)
import palette

GRID_SIZE = [0x100, 0x100]
GRID_FLATSIZE = GRID_SIZE[0] * GRID_SIZE[1]

CsSF_Biom = Struct(
    "magic" / Const(0x105, UInt16),
    "_numBiomes" / Rebuild(UInt32, len_(this.biomeIds)),
    "biomeIds" / UInt32[this._numBiomes],
    Const(2, UInt32),
    Const(GRID_SIZE, UInt32[2]),
    Const(GRID_FLATSIZE, UInt32),
    "biomeGridN" / UInt32[GRID_FLATSIZE],
    Const(GRID_FLATSIZE, UInt32),
    "resrcGridN" / UInt8[GRID_FLATSIZE],
    Const(GRID_SIZE, UInt32[2]),
    Const(GRID_FLATSIZE, UInt32),
    "biomeGridS" / UInt32[GRID_FLATSIZE],
    Const(GRID_FLATSIZE, UInt32),
    "resrcGridS" / UInt8[GRID_FLATSIZE],
)

KNOWN_RESOURCE_IDS = (8, 88, 0, 80, 1, 81, 2, 82, 3, 83, 4, 84)

with open(Path(__file__).parent.resolve() / "./biomes.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=("edid", "id", "name"))
    KNOWN_BIOMES = {int(x["id"], 16): (x["edid"], x["name"]) for x in reader}


def get_biome_names(id):
    entry = KNOWN_BIOMES.get(id, None)
    return entry if entry else (str(id), str(id))


class BiomFile(object):
    def __init__(self):
        self.planet_name = None
        self.biomeIds = set()
        self.resourcesPerBiomeId = dict()
        self.biomeGridN = []
        self.resrcGridN = []
        self.biomeGridS = []
        self.resrcGridS = []

    def load(self, filename):
        assert filename.endswith(".biom")
        with open(filename, "rb") as f:
            data = CsSF_Biom.parse_stream(f)
            assert not f.read()
        self.biomeIds = tuple(data.biomeIds)
        self.biomeGridN = np.array(data.biomeGridN)
        self.biomeGridS = np.array(data.biomeGridS)
        self.resrcGridN = np.array(data.resrcGridN)
        self.resrcGridS = np.array(data.resrcGridS)
        resourcesPerBiomeId = {biomeId: set() for biomeId in self.biomeIds}
        for i, biomeId in enumerate(self.biomeGridN):
            resourcesPerBiomeId[biomeId].add(self.resrcGridN[i])
        for i, biomeId in enumerate(self.biomeGridS):
            resourcesPerBiomeId[biomeId].add(self.resrcGridS[i])
        self.resourcesPerBiomeId = resourcesPerBiomeId
        self.biomesDesc = {
            "{}_{}".format(get_biome_names(id), id): sorted(value)
            for id, value in self.resourcesPerBiomeId.items()
        }
        self.planet_name = Path(filename).stem
        print(f"Loaded '{filename}'.")

    def save(self, filename):
        assert filename.endswith(".biom")
        obj = dict(
            biomeIds=sorted(set(self.biomeGridN) | set(self.biomeGridS)),
            biomeGridN=self.biomeGridN,
            biomeGridS=self.biomeGridS,
            resrcGridN=self.resrcGridN,
            resrcGridS=self.resrcGridS,
        )
        
        assert len(self.biomeGridN) == 0x10000
        assert len(self.biomeGridS) == 0x10000
        assert len(self.resrcGridN) == 0x10000
        assert len(self.resrcGridS) == 0x10000
        with open(filename, "wb") as f:
            CsSF_Biom.build_stream(obj, f)
        print(f"Saved '{filename}'.")

    def imgToArray(self):
        b2i = {i: id for i, id in enumerate(self.biomeIds)}
        b2n = {get_biome_names(id): id for id in self.biomeIds}
        r2i = {i: id for i, id in enumerate(KNOWN_RESOURCE_IDS)}

        print("b2i", b2i)
        print("b2n", b2n)
        print("r2i", r2i)

        res_array = np.asarray(self.res_img)

        
        empty_array = np.zeros((512,256,1))
        res_array = np.select(
            [res_array == palette.palettedata_lists[idx] for idx in r2i.keys()],
            [res_id for res_id in r2i.values()],
            empty_array
        )
        res_array = res_array[:, :, 0:1]
        res_array = res_array.astype(int)
        res_array = np.hsplit(res_array.ravel(), (65536,))

        self.resrcGridN = np.rot90(np.reshape(res_array[1], GRID_SIZE), axes=(1,0)).ravel()
        self.resrcGridS = np.rot90(np.reshape(res_array[0], GRID_SIZE), axes=(1,0)).ravel()

        biom_array = np.asarray(self.biom_img)

        biom_array = np.select(
            [biom_array == palette.palettedata_lists[idx] for idx in b2i.keys()],
            [biom_id for _, biom_id in b2i.items()],
            empty_array
        )
        biom_array = biom_array[:, :, 0:1]
        biom_array = biom_array.astype(int)
        biom_array = np.hsplit(biom_array.ravel(), (65536,))

        self.biomeGridN = np.rot90(np.reshape(biom_array[1], GRID_SIZE), axes=(1,0)).ravel()
        self.biomeGridS = np.rot90(np.reshape(biom_array[0], GRID_SIZE), axes=(1,0)).ravel()
        # Biome IDs
        unique = np.unique(biom_array)
        self.biomeIds = tuple([i for i in self.biomeIds if i in unique])
        print(self.biomeIds)

    def texture(self):
        b2i = {id: i for i, id in enumerate(self.biomeIds)}
        b2n = {id: get_biome_names(id) for id in self.biomeIds}
        r2i = {id: i for i, id in enumerate(KNOWN_RESOURCE_IDS)}

        print(b2n)

        biomeIdxGridN = np.reshape([b2i[x] for x in self.biomeGridN], GRID_SIZE)
        biomeIdxGridS = np.reshape([b2i[x] for x in self.biomeGridS], GRID_SIZE)
        resIdxGridN = np.reshape([r2i[x] for x in self.resrcGridN], GRID_SIZE)
        resIdxGridS = np.reshape([r2i[x] for x in self.resrcGridS], GRID_SIZE)

        biomeIdxGrid = np.hstack((biomeIdxGridN, biomeIdxGridS))
        resIdxGrid = np.hstack((resIdxGridN, resIdxGridS))

        combinedGrid = (resIdxGrid + 1) * len(b2i) + biomeIdxGrid * 2

        biome_idx_img = Image.fromarray(np.uint8(np.rot90(biomeIdxGrid))).convert('LA')
        biome_idx_img.putpalette(palette.palettedata)

        res_idx_img = Image.fromarray(np.uint8(np.rot90(resIdxGrid))).convert('LA')
        res_idx_img.putpalette(palette.palettedata)

        self.biome_idx_img = biome_idx_img.convert('RGB')
        self.res_idx_img = res_idx_img.convert('RGB')
        print("BIOME COLORS", biome_idx_img.getcolors())
        print("RES COLORS", self.res_idx_img.getcolors())