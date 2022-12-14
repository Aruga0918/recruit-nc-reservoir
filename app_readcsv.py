# -*- coding: utf-8 -*-
import app_base
import numpy as np


###############################################################################
# Common
###############################################################################
class Parameters(app_base.Parameters):
    def __init__(self, parser):
        super().__init__(parser)

    def add_hyper_parameters(self, parser):
        # Hyper parametes for reserver computing 
        parser.add_argument('-node', dest='node', default=800, type=int, help='number of node')
        parser.add_argument('-density', dest='density', default=0.2, type=float, help='density')
        parser.add_argument('-input_scale', dest='input_scale', default=0.004, type=float, help='input scale')
        parser.add_argument('-rho', dest='rho', default=0.999, type=float, help='rho')
        parser.add_argument('-fb_scale', dest='fb_scale', default=None, type=float, help='fb scale')
        parser.add_argument('-leaking_rate', dest='leaking_rate', default=0.1, type=float, help='leaking rate')
        parser.add_argument('-average_window', dest='average_window', default=1, type=int, help='average window size')
        parser.add_argument('--no_classification', dest='no_class', action='store_false', help='no class')


    def add_custome_perametes(self, parser):
        parser.add_argument('-num_of_input_data', dest='num_of_input_data', default=1, type=int, help='num of input data (num of sensors)')
        parser.add_argument('-num_of_output_classes', dest='num_of_output_classes', default=1, type=int, help='num of output claasses')
        parser.add_argument('-training_time_in_sec', dest='training_time_in_sec', default=60, type=int, help='Training time in sec')

    def set_parameters(self, params):
        self.node = params.node
        self.density = params.density
        self.input_scale = params.input_scale
        self.rho = params.rho
        self.fb_scale = params.fb_scale
        self.leaking_rate = params.leaking_rate
        self.average_window = params.average_window
        self.no_class = params.no_class

        self.num_of_input_data = params.num_of_input_data
        self.num_of_output_classes = params.num_of_output_classes
        self.training_time_in_sec = params.training_time_in_sec



class DataAugmentation(app_base.DataAugmentation):
    def __init__(self, parameters=[]):
        self.parameters = parameters

    def get_augmented_data(self, pulse):
        return pulse


###############################################################################
# Train
###############################################################################
class TrainingApp:
    def __init__(self, parametes):
        #super().__init__()
        self.parametes = parametes
    

    def get_data(self, data):
        pulse00 = data[1] #Aruga modified : 0 to 1 22/10/31
        #pulse01 = data[1]
        #pulse02 = data[2]
        #pulse03 = data[3]
        buttons = data[3] #Aruga modified : 4 to 3 22/10/31
        return pulse00, buttons

    def prepare_data(self, data):
        pulse00, label = self.get_data(data)
        pulses = [float(pulse00),]
        labels = [float(int(label) == 1), ]#Aruga modified : 2 to 1 22/10/31
        # if int(label) == 1: #Aruga modified : 2 to 1 22/10/31
        #     if self.is_thumb_neutral == True:
        #         #pygame.event.post(self.E_THUMB_UP)
        #         self.is_thumb_neutral = False
        # else:
        #     if self.is_thumb_neutral != True | self.is_thumb_neutral == None: #Aruga modified : add None 22/10/31
        #         #pygame.event.post(self.E_THUMB_NEUTRAL)
        #         self.is_thumb_neutral = True

        return pulses, labels

    def is_alive(self):
        return super().is_alive()


###############################################################################
# Predict
###############################################################################
# import pygame
import time

class PredictApp:
    def __init__(self, parametes):
        self.parametes = parametes
        # self.width = 151
        # self.height = 181 + 50
        # self.display = pygame.display.set_mode((self.width, self.height))

        # self.font = pygame.font.SysFont("Arial", 35)
        # white = (230, 230, 230)
        # self.title = self.font.render('Predict', True, white)
        # self.title_rect = self.title.get_rect(topright = (110, 185))
        # self.bg_thumb_neutral = pygame.image.load("thumb_neutral.png")
        # self.bg_thumb_up = pygame.image.load("thumb_up.png")
        # self.bg = self.bg_thumb_neutral
        # self.E_THUMB_NEUTRAL = pygame.event.Event(pygame.USEREVENT, attr1='E_THUMB_NEUTRAL')
        # self.E_THUMB_UP      = pygame.event.Event(pygame.USEREVENT, attr1='E_THUMB_UP')
        # pygame.display.set_caption("Reservoir Computing - thumb up detection")
        # self.clock = pygame.time.Clock()
        self.data0 = DataAugmentation(self.parametes)
        self.is_thumb_neutral = True
        self.moving_avg_win_size = 4

    #def close(self):
    #    pygame.quit()
    #    sys.exit()
    

    def get_data(self, data):
        pulse00 = data[0]
        #pulse01 = data[1]
        #pulse02 = data[2]
        #pulse03 = data[3]
        buttons = data[4]
        return pulse00

    def prepare_data(self, data):
        pulse00 = self.get_data(data)
        pulses = [float(pulse00),]
        print("prepare_data_done")

        return pulses

    def set_predict_result(self, predicted):
        super().set_predict_result(predicted)
        if len(predicted[-self.moving_avg_win_size:-1]) == 0:
            print('P skip02')
            return

        avg = np.mean(predicted[-self.moving_avg_win_size:-1][0][0])

        if avg > 0.5:
            if self.is_thumb_neutral == True:
                #pygame.event.post(self.E_THUMB_UP)
                self.is_thumb_neutral = False
        else:
            if self.is_thumb_neutral != True:
                #pygame.event.post(self.E_THUMB_NEUTRAL)
                self.is_thumb_neutral = True
        return

    def is_alive(self):
        return super().is_alive()


if __name__=="__main__":
    training_app = TrainingApp()

