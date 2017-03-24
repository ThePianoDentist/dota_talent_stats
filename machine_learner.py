from keras.models import Sequential
from keras.layers import Dense
import numpy

seed = 7  # random seed fixed so can reproduce things
numpy.random.seed(seed)

class Model:
    def __init__(self):
        self.model = None
        self.inputs = None
        self.outputs = None

    def predict(self, input_):
        return self.model.predict(input_)

    def evaluate(self):
        scores = self.model.evaluate(self.inputs, self.outputs)
        print("Evaluation: \n")
        print(scores)
        print("%s: %.2f%%" % (self.model.metrics_names[1], scores[1] * 100))


class SimpleModel(Model):
    pass


class DiscreteHeroModel(Model):

    def __init__(self, inputs, outputs):
        """

        :param inputs: the discrete representations of possible heros
            - plus the 4 talent choices
            - 0.5 represents never chose that talent
        :param outputs: 1 for win. 0 for loss :)
        """
        super().__init__()
        self.inputs = numpy.array(inputs)
        self.outputs = numpy.array(outputs)

        self.model = Sequential()
        # TODO 80, 40, 72000. whats a number ¯\_(ツ)_/¯
        self.model.add(Dense(260, input_dim=230, init='uniform', activation='relu'))
        self.model.add(Dense(130, init='uniform', activation='relu'))
        self.model.add(Dense(1, init='uniform', activation='sigmoid'))
        print(len(self.inputs))
        print(len(self.outputs))
        self.model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        self.model.fit(self.inputs, self.outputs, nb_epoch=150, batch_size=10)


class DecomposedHeroModel(Model):
    pass


class Net:

    def __init__(self, inputs, outputs):
        self.inputs = inputs
        self.outputs = outputs

        # inputs
        # 4 friendly team-mates
        # our hero
        # 5 enemies
        #
        # ouput w/l
        # hmmmmmmmmmmmmmm
        # so the input arent numerical values where differences have meaning...they're just ids
        # this isnt really a machine learning problem?
        # this is more, we have different estimates with different errors
        # how to combine to make most accurate guess :/
        # as in we may have a game with these exact heroes and won it. but that 100% is less reliable
        # than 1000s of games with a few hero matches with maybe 60% winrate

        # so standard error = standard deviation / sqrt(sample size)

        model = Sequential()

        # random note: rectifier funcs over sigmoids > performance (dont do for output layer)