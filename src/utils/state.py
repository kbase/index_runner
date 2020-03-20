class AppState:
    def __init__(self, file):
        self.file = file

    def starting(self):
        with open(self.file, 'w') as f:
            f.write('starting')

    def ready(self):
        with open(self.file, 'w') as f:
            f.write('ready')

    def done(self):
        with open(self.file, 'w') as f:
            f.write('done')

    def error(self, message):
        with open(self.file, 'w') as f:
            f.write('error')
            f.write(message)
