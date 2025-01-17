import torch.nn.functional as F
import torch.nn as nn

class BKNet(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(11, 24)
        self.fc2 = nn.Linear(24, 24)
        self.fc3 = nn.Linear(24, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        x = x[:, -1, :]

        return x

class Net(nn.Module):
    def __init__(self, input_shape=31, nb_classes=11):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(input_shape, 64)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(64, 32)
        self.relu2 = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.fc3 = nn.Linear(32, nb_classes)
        # self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.dropout(x)
        x = self.fc3(x)
        # x = self.softmax(x)
        return x
    
class BKNet(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(11, 24)
        self.fc2 = nn.Linear(24, 24)
        self.fc3 = nn.Linear(24, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        x = x[:, -1, :]

        return x


class OriginalNet(nn.Module):
    def __init__(self):
        super(OriginalNet, self).__init__()

        self.fc1 = nn.Linear(11, 24)
        self.fc2 = nn.Linear(24, 24)
        self.fc3 = nn.Linear(24, 24)
        self.fc4 = nn.Linear(24, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        x = x[:, -1, :]

        return x