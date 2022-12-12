# Hernando M. Vergara, SWC
# February 2021
# Save_resolution_and_channel_from_czi.py
# Creates 16-bit .tif files for every slice from a czi file from the slide scanner,
# saving one channel, from a defined piramid, at a desired resolution

# This can be used as a complement to CZI_SlideScanner_ROIsubdivider.py

from ij import IJ  #, ImagePlus, ImageStack
from loci.formats import ImageReader
from ij.plugin import ContrastEnhancer, RGBStackMerge
from os import path, makedirs
# import sys
# sys.path.append(path.abspath(path.dirname(__file__)))
from czi_rs_functions.czi_structure import get_data_structure, get_binning_factor, open_czi_series, \
    get_maxres_indexes
from czi_rs_functions.image_manipulation import extractChannel


channels_to_save = [2] # array of channels to save
final_resolution = 20 # resolution desired (microns/px)
piramid_to_open = 3 # if you know your data, open the closest resolution (but higher) to the desired one.
# that way it runs faster. Use 1 for being cautious.

# Main
if __name__ in ['__builtin__', '__main__']:
    # get the file
    input_path = IJ.getFilePath("Choose a .czi file")
    reader = ImageReader()
    reader.setId(input_path)
    metadata_list = reader.getCoreMetadataList()
    # slide scanner makes a piramid of X for every ROI you draw
    # resolution is not updated in the metadata so it needs to be calculated manually
    number_of_images, num_of_piramids_list = get_data_structure(metadata_list)
    IJ.log("Number of images is " + str(number_of_images))
    # set names of subimages in the list, waiting to compare to current outputs
    file_core_name = path.basename(input_path).split('.czi')[0]
    # get the indexes of the maximum resolution images
    max_res_indexes = get_maxres_indexes(num_of_piramids_list)
    IJ.log("Number of pyramids are " + str(num_of_piramids_list))
    # set names of subimages in the list, waiting to compare to current outputs
    possible_slices = [file_core_name + "_slice-" + str(n)
                       for n in range(number_of_images)]

    binFactor_list, binStep_list = get_binning_factor(max_res_indexes,
                                                      num_of_piramids_list, metadata_list)
    IJ.log("Binning factors are " + str(binFactor_list))
    IJ.log("Binning steps are " + str(binStep_list))

    # create output directory if it doesn't exist
    output_res_path = 'Registration/Slices_for_ARA_registration_' + str(final_resolution) + '-umpx'
    animal_id = file_core_name.split('_')[0]
    output_path = path.join(path.dirname(path.dirname(input_path)),
                            "Processed_data", animal_id, output_res_path)
    if path.isdir(output_path):
        print("Output path was already created")
    else:
        makedirs(output_path)
        print("Output path created")

    # for each slice name:
    for sl_name in possible_slices:
        # parse the slice number
        sl_num = int(sl_name.split('-')[-1])
        print("Processing image " + sl_name)
        # get info
        num_of_piramids = num_of_piramids_list[sl_num]
        binFactor = binFactor_list[sl_num]
        high_res_index = max_res_indexes[sl_num]
        binStep = binStep_list[sl_num]
        # open the image
        # get the Xth resolution binned, depending on the number
        # of resolutions. The order is higher to lower.
        series_num = high_res_index + piramid_to_open
        raw_image = open_czi_series(input_path, series_num)
        # save the resolution (every image has the high-resolution information)
        res_xy_size = raw_image.getCalibration().pixelWidth
        res_units = raw_image.getCalibration().getXUnit()

        if len(channels_to_save) > 1:
            imps = []

        for channel_to_save in channels_to_save:
            # select the requested channel and adjust the intensity
            regist_image = extractChannel(raw_image, channel_to_save, 1)
            # TODO: test if contrast enhancement and background sustraction are needed for registration
            ContrastEnhancer().stretchHistogram(regist_image, 0.35)
            # IMPLEMENT BACKGROUND SUSTRACTION HERE
            regist_image.setTitle(sl_name)
            #ch_image.show()
            
            # convert to Xum/px so that it can be aligned to ARA
            reg_im_bin_factor = binStep ** piramid_to_open
            regres_resolution = reg_im_bin_factor * res_xy_size
            rescale_factor = regres_resolution / final_resolution
            new_width = int(rescale_factor * regist_image.getWidth())
            # self.lr_dapi_reg.getProcessor().scale(rescale_factor, rescale_factor)
            ip = regist_image.getProcessor().resize(new_width)
            regist_image.setProcessor(ip)
            
            if len(channels_to_save) > 1:
                imps.append(regist_image)

        # clean
        raw_image.close()
        raw_image.flush()
            
        # merge images
        if len(channels_to_save) > 1:
            regist_image = RGBStackMerge.mergeChannels(imps, False)
            
        # Add the information to the metadata
        regist_image.getCalibration().pixelWidth = final_resolution
        regist_image.getCalibration().pixelHeight = final_resolution
        regist_image.getCalibration().pixelDepth = 1
        regist_image.getCalibration().setXUnit("microns")
        regist_image.getCalibration().setYUnit("microns")
        regist_image.getCalibration().setZUnit("microns")
        # Save image
        reg_slice_name = path.join(output_path, sl_name)
        IJ.saveAsTiff(regist_image, reg_slice_name)
        regist_image.close()
        regist_image.flush()
    print("Done")
    print("See your images in {}".format(output_path))
