from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import *
from core.services import ingest

# (topic, [(doc title, kind, location, text)])
DATA = {
 "Linear Regression": [
  ("ML Textbook", "pdf", "Page 12", "Linear regression models the relationship between a dependent variable and one or more input features using a straight line. The model predicts a continuous target by multiplying each feature by a weight and adding a bias term. Linear regression is the simplest supervised learning method for predicting numbers."),
  ("ML Textbook", "pdf", "Page 13", "Training a linear regression model means choosing the weights that minimise the mean squared error between predictions and true targets. The error is the squared difference between each prediction and the actual value, averaged across the dataset. A smaller mean squared error means the regression line fits the data better."),
  ("Lecture 3 Slides", "pptx", "Slide 5", "Each weight in a linear regression describes how much the prediction changes when its feature increases by one unit. The bias term shifts the regression line up or down. Interpreting weights makes linear regression easy to explain to non-experts."),
  ("Lecture 3 Video", "video", "4:10", "So remember, linear regression assumes the target is a weighted sum of the features, and we fit that weighted sum by minimising the squared error. If the relationship is curved, a straight regression line will underfit the data.")],
 "Gradient Descent": [
  ("ML Textbook", "pdf", "Page 21", "Gradient descent is an optimisation algorithm that minimises a loss function by repeatedly moving the parameters in the direction opposite to the gradient. The gradient points toward the steepest increase of the loss, so stepping backwards reduces it. Gradient descent is used to train linear models and neural networks."),
  ("ML Textbook", "pdf", "Page 22", "The learning rate controls the size of each gradient descent step. A learning rate that is too large makes the loss bounce around or diverge, while a learning rate that is too small makes training painfully slow. Choosing a good learning rate is one of the most important decisions in gradient descent."),
  ("Lecture 3 Slides", "pptx", "Slide 11", "Stochastic gradient descent updates the parameters using a small random batch of examples instead of the full dataset. Each batch gives a noisy estimate of the gradient, but the updates are much cheaper. Stochastic gradient descent scales to very large datasets."),
  ("Lecture 3 Video", "video", "18:45", "Picture the loss as a valley and gradient descent as a ball rolling downhill. The gradient tells the ball which way is downhill, and the learning rate decides how big each step is. If the learning rate is too large the ball overshoots the valley floor.")],
 "Overfitting & Regularization": [
  ("ML Textbook", "pdf", "Page 34", "Overfitting happens when a model memorises noise in the training data and then performs poorly on new data. An overfit model has very low training error but high validation error. Overfitting is more likely when the model is complex and the training set is small."),
  ("ML Textbook", "pdf", "Page 35", "Regularization reduces overfitting by adding a penalty on large weights to the loss function. L2 regularization penalises the squared size of the weights, while L1 regularization penalises their absolute size and can push some weights to exactly zero. Regularization trades a little training accuracy for better generalization."),
  ("Lecture 3 Slides", "pptx", "Slide 17", "A validation set is held out from training to measure generalization honestly. If validation error rises while training error keeps falling, the model is overfitting. Early stopping halts training at the point where validation error is lowest."),
  ("Lecture 3 Video", "video", "31:20", "The goal of regularization is generalization, not a perfect score on training data. Cross-validation repeats the train and validation split several times so that the estimate of generalization is more reliable.")],
 "Neural Networks": [
  ("ML Textbook", "pdf", "Page 48", "A neural network is built from layers of neurons, where each neuron computes a weighted sum of its inputs and passes the result through an activation function. Stacking layers lets a neural network learn complicated non-linear patterns. The hidden layers between input and output build progressively more abstract features."),
  ("ML Textbook", "pdf", "Page 49", "Activation functions such as ReLU and sigmoid introduce non-linearity into a neural network. Without an activation function, stacked layers would collapse into a single linear transformation. ReLU outputs zero for negative inputs and the input itself otherwise, which keeps training fast."),
  ("Lecture 3 Slides", "pptx", "Slide 24", "Backpropagation computes the gradient of the loss with respect to every weight in a neural network by applying the chain rule layer by layer from the output backwards. Gradient descent then uses these gradients to update the weights. Backpropagation makes training deep networks practical."),
  ("Lecture 3 Video", "video", "44:05", "A forward pass sends the input through every layer to produce a prediction, and backpropagation sends the error backwards to produce gradients. Repeat the forward pass and backpropagation over many batches and the neural network gradually improves.")],
}


class Command(BaseCommand):
    help = "OPTIONAL: create a sample course (PDF pages, slides and video timestamps) with topics and quiz questions."

    def add_arguments(self, parser):
        parser.add_argument("--user", default="demo@eduadapt.ai", help="Email of the account to give the sample course to")

    def handle(self, *args, **opts):
        owner, made = User.objects.get_or_create(username=opts["user"], defaults={"email": opts["user"], "first_name": "Demo Student"})
        if made: owner.set_unusable_password(); owner.save()
        Course.objects.filter(owner=owner, name="Intro to Machine Learning").delete()
        course = Course.objects.create(name="Intro to Machine Learning", owner=owner)
        docs, prev = {}, None
        for i, (tname, items) in enumerate(DATA.items()):
            topic = Topic.objects.create(course=course, name=tname, order=i)
            if prev: topic.prerequisites.add(prev)
            prev = topic
            for title, kind, loc, text in items:
                doc = docs.get(title) or docs.setdefault(title, Document.objects.create(course=course, title=title, kind=kind))
                Chunk.objects.create(document=doc, topic=topic, text=text, location=loc)
        ingest.generate_questions(course)
        self.stdout.write(self.style.SUCCESS(f"Demo ready: {course.topics.count()} topics, {Question.objects.filter(topic__course=course).count()} questions."))
