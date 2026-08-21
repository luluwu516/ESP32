import keras_lite_convertor as kc

from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

DATA_FILE = "temperature.txt"
MODEL_FILE = "temperature_model.json"

Data_reader = kc.Data_reader(DATA_FILE, mode="regression")
data, label = Data_reader.read(random_seed=12)

# data processing
split_idx = int(len(data) * 0.85)
train_data = data[:split_idx]
train_label = label[:split_idx]

# normalization
mean = train_data.mean()
std = train_data.std()
data -= mean
data /= std

label /= 100

# validation
validation_data = data[split_idx:-5]
validation_label = label[split_idx:-5]

# test
test_data = data[-5:]
test_label = label[-5:]

print(
    "train",
    train_data.shape,
    " validation",
    validation_data.shape,
    " test",
    test_data.shape,
)

model = Sequential()

# activate function: ReLU
model.add(layers.Dense(20, activation="relu", input_shape=(1,)))
model.add(layers.Dense(20, activation="relu"))
model.add(layers.Dense(20, activation="relu"))
model.add(layers.Dense(1))
model.summary()


model.compile(optimizer="adam", loss="mse", metrics=["mae"])
train_history = model.fit(
    train_data,
    train_label,
    validation_data=(validation_data, validation_label),
    epochs=1000,
)

prediction = model.predict(test_data).flatten() * 100
groundtruth = test_label.flatten() * 100

print()
for p, g in zip(prediction, groundtruth):
    print("predict %.2fC actual %.2fC error: %+.2f" % (p, g, p - g))

kc.save(model, MODEL_FILE)

print()
print("mean =", mean)
print("std =", std)
