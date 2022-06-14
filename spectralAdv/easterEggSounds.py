from pygame import mixer # Load the required library
import os

Trek_sounds = {'open_image': 'tos_com_beep_3.mp3',
               'classAnalysis': 'hail_allship_ep.mp3',
               'material_identification': 'romulan_transporter.mp3',
                'other': 'hail_allship_ep.mp3'}

sound_classes = {'Trek': Trek_sounds}

def play(sound_class, sound_type):

    # retrun if no sound class is passed
    if sound_class == None:
        return

    sounds = sound_classes[sound_class]
    if sound_type in sounds.keys():
        sound = sounds[sound_type]
    else:
        sound = sounds['other']

    mixer.init()
    mixer.music.load(os.path.join(os.getcwd(), sound))
    mixer.music.play()

