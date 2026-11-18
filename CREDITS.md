## Footprint Library Credits

The credits of 3D models are listed in respective folder.  
Please fill all 3D models credits and info source data accordingly.  

### Info requirements:
- Author
- if the 3D model is script generated, a link to the script generator is required as well as the version and sw used
- if the 3D model is manually generated, include the source model @ https://github.com/KiCad/packages3D-source

### Models added to Trace's copy after the KiCad 10.0.0 import
This repository started as KiCad's 3D model library at tag 10.0.0. These files were later copied
unchanged from the official KiCad library (https://gitlab.com/kicad/libraries/kicad-packages3D),
under the same licence (LICENSE.md), because Trace's stock footprints name them:

- From KiCad tag 10.0.8 (KiCad commit e62ed1fc, "Capacitor THT: Re-add 7.2mm 5mm pitch generated parts"):
  `Capacitor_THT.3dshapes/C_Rect_L7.2mm_W{2.5,3.5,4.5,5.0,6.0,7.2}mm_P5.00mm.step`
- From KiCad tag 10.0.8 (KiCad commit 2917d029):
  `Package_DFN_QFN.3dshapes/Texas_RNQ0040A_WQFN-40-1EP_6x4mm_P0.4mm_EP4.7x2.7mm.step`
- From KiCad tag 10.0.8 (KiCad commit 0bc64e92):
  `Package_DFN_QFN.3dshapes/WQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm.step`
- `Package_LGA.3dshapes/Infineon_PG-TSNP-6-10_0.7x1.1mm_0.7x1.1mm_P0.4mm.step` is a copy of KiCad's
  `Package_DFN_QFN.3dshapes/` file of the same name (KiCad commit 121ca5f2, Carlos Nieves Ónega),
  placed where the `Package_LGA` footprint looks for it.
