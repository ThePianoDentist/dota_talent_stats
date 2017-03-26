import random

from keras.models import Sequential
from keras.layers import Dense
import numpy
import itertools

seed = 7  # random seed fixed so can reproduce things
numpy.random.seed(seed)

# TODO abstract model stuff away so can literally just give our hero id, and team and enemy ids.
# TODO i.e dont hardcode these numpy.zeros(230) everywhere


class Model:
    def __init__(self, inputs, outputs, model, alpha, test_inputs, test_outputs):
        self.model = model
        self.inputs = inputs
        self.outputs = outputs
        self.ignoreHeroes = False
        self.alpha = alpha  # for http://stats.stackexchange.com/a/136542
        self.test_inputs = test_inputs
        self.test_outputs = test_outputs

    def _net_predict(self, input_):
        if self.ignoreHeroes:
            input_ = input_[-4:]
        return self.model.predict(numpy.array([input_]))

    @property
    def neuron_upper_limit(self):
        # TODO assumes only 1 output field
        import pdb; pdb.set_trace()
        upper_limit = len(self.inputs) / (self.alpha * (len(self.inputs[0]) + 1))
        return upper_limit

    def evaluate(self):
        scores = self.model.evaluate(self.inputs, self.outputs)
        print("Evaluation: \n")
        print(scores)
        print("%s: %.2f%%" % (self.model.metrics_names[1], scores[1] * 100))

    def predict(self, our_hero, friendly_heroes, enemy_heroes):
        inputs = numpy.empty(230)
        inputs.fill(-1.0)
        for h in friendly_heroes:
            inputs[DiscreteHeroModel.hero_id_to_index(h, our_hero.id, True)] = 1.0
        for h in enemy_heroes:
            inputs[DiscreteHeroModel.hero_id_to_index(h, our_hero.id, False)] = 1.0

        skill_trees = [list(i) for i in itertools.product([-1.0, 1.0], repeat=4)]
        for sk_tree in skill_trees:
            temp_inputs = inputs
            temp_inputs[-4:] = sk_tree
            prediction = self._net_predict(temp_inputs)
            rounded = [round(x[0], 4) for x in prediction]
            print("\nSkill tree:")
            print(temp_inputs[-4:])
            print("\nPrediction: ")
            print(rounded)

    def test(self):
        # TODO whats the best way to measure accuracy?
        # do i need to be checking std_devs of inaccuracies as well?
        inaccuracy = 0.0
        actual_out_sum = predicted_out_sum = 0.0
        for i, input_ in enumerate(self.test_inputs):
            predicted_out = self._net_predict(input_)[0]
            actual_out = self.test_outputs[i]
            inaccuracy += abs(actual_out - predicted_out)
            predicted_out_sum += predicted_out
            actual_out_sum += actual_out
        #inaccuracy /= len(self.test_outputs)
        inaccuracy = abs(actual_out_sum - predicted_out_sum) / len(self.test_inputs)
        print("Actual winrate: ", actual_out_sum/ len(self.test_inputs))
        print("Predicted winrate: ", predicted_out_sum / len(self.test_inputs))
        return inaccuracy



class SimpleModel(Model):
    pass

class RandomForestDeicisonTreeModel(Model):
    "does the 100 or so branches for each choice make this kind of hard? / poor performance?"
    "could do same thing and turn it into binary choices to choose a hero or not"
    "but just trading width for height"
    pass

class DiscreteHeroModel(Model):

    def __init__(self, inputs, outputs, alpha=2, test_inputs=None, test_outputs=None, ignore_heroes=False):
        """

        :param inputs: the discrete representations of possible heros
            - plus the 4 talent choices
            - 0.5 represents never chose that talent
        :param outputs: 1 for win. 0 for loss :)
        """
        self.ignoreHeroes = ignore_heroes
        # TODO tidy how inheritance occurring. how consturctors behave. this is messy
        if self.ignoreHeroes:
            self.inputs = numpy.array([inp[-4:] for inp in inputs])
            self.test_inputs = numpy.array([inp[-4:] for inp in test_inputs])
            dimension = 4
        else:
            self.inputs = numpy.array(inputs)
            self.test_inputs = numpy.array(test_inputs)
            dimension = 230
        self.outputs = numpy.array(outputs)
        self.test_outputs = numpy.array(test_outputs)

        self.model = Sequential()
        # TODO 80, 40, 72000. whats a number ¯\_(ツ)_/¯
        self.model.add(Dense(115, input_dim=dimension, init='uniform', activation='relu'))
        #self.model.add(Dense(260, input_dim=230, init='uniform', activation='relu'))
        # self.model.add(Dense(133, init='uniform', activation='relu'))
        # self.model.add(Dense(8, init='uniform', activation='relu'))
        self.model.add(Dense(1, init='uniform', activation='sigmoid'))
        print(len(self.inputs))
        print(len(self.outputs))
        self.model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
        self.model.fit(self.inputs, self.outputs, epochs=150, batch_size=10)
        super().__init__(self.inputs, self.outputs, self.model, alpha, self.test_inputs, self.test_outputs)

    @staticmethod
    def hero_id_to_index(hero_id, our_hero_id, friendly):
        start = 0 if friendly else 113
        if hero_id < our_hero_id:
            return start + hero_id - 1  # hero_ids start at 1, not 0
        else:
            return start + hero_id - 2  # we 'jump over' our_hero in the array

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