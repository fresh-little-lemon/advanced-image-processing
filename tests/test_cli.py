import subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from reliable_focus.io import read_rgb

class CliTests(unittest.TestCase):
    def test_cli_average(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            for name,value in [('a',20),('b',220)]:
                Image.fromarray(np.full((9,11,3),value,dtype=np.uint8)).save(folder/f'{name}.png')
            subprocess.run([sys.executable,'-m','reliable_focus.cli',str(folder/'a.png'),str(folder/'b.png'),str(folder/'out.png'),'--method','average'],check=True,capture_output=True)
            np.testing.assert_allclose(read_rgb(folder/'out.png'),120/255)
    def test_grayscale_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'gray.png';Image.fromarray(np.zeros((9,9),dtype=np.uint8)).save(path)
            with self.assertRaises(ValueError):read_rgb(path)
