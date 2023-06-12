import sys, subprocess
import os.path as op, os, io
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QTreeView, QFileSystemModel, QSplitter, QScrollArea, QToolTip
from PyQt5.QtGui import QImage, QPixmap, QCursor
from PyQt5.QtCore import Qt, QSize, QDir, QUrl,QModelIndex
import winsound
from pydub import AudioSegment
import cv2
import numpy as np

WINDOW_TITLE = "SoXspectroGUI"

DEFAULT_ROOT = "" # root (should be "" for "My Computer")
DEFAULT_SELECT = "C:/Users/"  # Set the default selected path

MAINWIN_W = 1280
MAINWIN_H = 720
folder_viewH = 300
folder_viewW = 700

SoXSpectroW = 800 #default 800
SoXSpectroH = 256 # for one channel

DO_SAVE_TO_SUBFOLDER = False # whether to save the spectrograms to a subfolder
SUBFOLDER_NAME = "Spectrograms"

AUDIO_FORMATS = ('.flac', '.wav', '.mp3', '.ogg') # list of file extentions to be parsed

SoXPath = 'sox' # path to the sox / use 'sox' if SoX is in path environment variable

# test if sox is installed
try:
    subprocess.check_output([SoXPath, '--version'])
except (subprocess.CalledProcessError, FileNotFoundError):
    raise FileNotFoundError("SoX may not be installed. Please set the path to sox.exe in the settings")

# arg handling (for sendto)
sysargs = sys.argv

if len(sysargs) == 2 and op.isdir(sysargs[1]):
    # if only one argument that is a folder, should not throw an error
    DEFAULT_SELECT = sysargs[1] #default to the folder
elif len(sysargs) > 1:
    # if multiple arguments (only the first arg will be used) or a single argument that is a file
    if op.isfile(sysargs[1]) or op.isdir(sysargs[1]):
        #in the case the first argument is a valid path
        DEFAULT_SELECT = op.dirname(sysargs[1]) #default to the folder containing them
    else:
        print("Invalid Argument, the selection will default to : " + DEFAULT_SELECT)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, MAINWIN_W, MAINWIN_H)  # Geometry   

        # Create a splitter to divide the main window into two parts
        self.splitter = QSplitter(Qt.Horizontal)

        self.folder_view_left = QTreeView(self)
        self.folder_view_left.setFixedHeight(folder_viewH)  # Set fixed height for the file view
        self.folder_view_left.setRootIsDecorated(True)
        self.folder_view_left.setHeaderHidden(False)
        self.folder_view_left.clicked.connect(self.folder_selected)

        self.folder_model_left = QFileSystemModel(self.folder_view_left)
        self.folder_model_left.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)  # Set filter to show only folders
        self.folder_model_left.setRootPath('')
        self.folder_view_left.setModel(self.folder_model_left)
        self.folder_view_left.setSelectionMode(QTreeView.SingleSelection)
        self.folder_view_left.header().resizeSection(0, folder_viewW)  # Adjust width of the first section (Name)
        default_index = self.folder_model_left.index(DEFAULT_SELECT)
        self.folder_view_left.setCurrentIndex(default_index)
        self.folder_view_left.setRootIndex(self.folder_model_left.index(DEFAULT_ROOT))
        self.folder_view_left.expand(default_index)

        self.folder_view_right = QTreeView(self)
        self.folder_view_right.setFixedHeight(folder_viewH)  # Set fixed height for the file view
        self.folder_view_right.setRootIsDecorated(True)
        self.folder_view_right.setHeaderHidden(False)

        self.folder_model_right = QFileSystemModel(self.folder_view_right)
        self.folder_model_right.setFilter(QDir.Files)   # Set filter to show only files
        self.folder_view_right.setModel(self.folder_model_right)
        self.folder_view_right.setSelectionMode(QTreeView.SingleSelection)
        self.folder_view_right.header().resizeSection(0, folder_viewW)  # Adjust width of the first section (Name)

        self.splitter.addWidget(self.folder_view_left)
        self.splitter.addWidget(self.folder_view_right)

        self.process_button = QPushButton("Process Audio", self)
        self.process_button.clicked.connect(self.process_audio)
        self.process_button.setEnabled(False)

        self.save_button = QPushButton("Save Images", self)
        self.save_button.clicked.connect(self.save_images)
        self.save_button.setEnabled(False)

        self.scroll_area = QScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)

        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        layout.addWidget(self.process_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.scroll_area)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.resizeEvent(None)

        self.selected_folder_path = ""
        self.images = []

        # Set the default directory
        self.folder_view_left.setCurrentIndex(self.folder_model_left.index(DEFAULT_SELECT))
        self.folder_view_left.setRootIndex(self.folder_model_left.index(DEFAULT_ROOT))
        
        # initial state of objects
        self.folder_selected(self.folder_view_left.currentIndex())

    def folder_selected(self, index):
        self.selected_folder_path = self.folder_model_left.filePath(index)

        # Get the count of audio files in the selected folder
        try:
            files = os.listdir(self.selected_folder_path)
            audio_files = [file for file in files if file.lower().endswith(AUDIO_FORMATS)]
            count = len(audio_files)
            if count > 0:
                self.process_button.setEnabled(True)

                # Update the text of the process_button
                self.process_button.setText(f"Process Audio ({count} audio files)")
            else:  # no files
                self.process_button.setEnabled(False)

                # Update the text of the process_button
                self.process_button.setText(f"Process Audio (0 audio files)")

            # Set the root index of the right file view to the selected folder
            self.folder_view_right.setRootIndex(self.folder_model_right.setRootPath(self.selected_folder_path))
                    
        except:
            print("Error accessing the folder")

    def process_audio(self):
        if not self.selected_folder_path:
            return
            
        files = os.listdir(self.selected_folder_path)
        audio_files = [file for file in files if file.lower().endswith(AUDIO_FORMATS)]

        total_files = len(audio_files)
        processed_files = 0

        # Clear the previous images from the scrollable layout and the images list
        self.clear_images()
        self.images = []

        for audio_file in audio_files:
            # showing progress
            processed_files += 1
            file_path = op.join(self.selected_folder_path, audio_file).replace("\\","/")
            self.setWindowTitle(f"Processing ({processed_files}/{total_files}) : {file_path}")

            with open(file_path, "rb") as file:
                print("Loading audio data... " + file_path)
                audio_data = file.read()
            
            # Decode audio data into WAV format using pydub
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
            wav_data = audio_segment.export(format='wav').read()

            command = [
                SoXPath,
                '-t', 'wav', '-', '-n',
                'spectrogram',
                '-o', '-',
                '-x', str(SoXSpectroW),
                '-y', str(SoXSpectroH),
                '-t',
                op.basename(file_path)
            ]
            print("Processing...")
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       shell=False)
            result, error = process.communicate(input=wav_data)

            # Check for any errors
            if process.returncode != 0:
                print("Error processing file:", audio_file)
                print("Error:", error.decode())
                continue

            # Load the image from the byte data
            image = QImage.fromData(result)

            # Create a QLabel to display the image
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setPixmap(QPixmap.fromImage(image))
            image_label.setScaledContents(True)
            image_label.setCursor(QCursor(Qt.PointingHandCursor))

            # Set tooltip with the audio file name
            image_label.setToolTip(audio_file)

            # Connect the click event to the image click handler
            image_label.mousePressEvent = self.create_image_click_handler(result, audio_file)

            # Add the image label to the scrollable layout
            self.scroll_layout.addWidget(image_label)

            # Add the image to the images list
            self.images.append((result, audio_file,self.selected_folder_path))

        self.setWindowTitle(WINDOW_TITLE)

        if self.images:
            self.save_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)
        print("Processing done")
        
    def play_complete_sound(self):
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)

    def clear_images(self):
        # Clear the scrollable layout
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        # Clear the images list
        self.images.clear()

    def save_images(self):
        if (DO_SAVE_TO_SUBFOLDER):
            os.mkdir( op.join(self.images[0][-1], SUBFOLDER_NAME) ) # creating the corresponding subfolder
        for image_data, audio_file, path in self.images:
            if (DO_SAVE_TO_SUBFOLDER): #saving to a subfolder
                file_path = op.join(op.join(path, SUBFOLDER_NAME), op.splitext(audio_file)[0] + ".png")
            else:
                file_path = op.join(path, op.splitext(audio_file)[0] + ".png")
            with open(file_path, "wb") as file:
                print("Writing image... " + file_path)
                file.write(image_data)
        print("Images saved successfully!")
        self.play_complete_sound()

    def create_image_click_handler(self, image_data, audio_file):
        def image_click_handler(event):
            # Decode the image data into a numpy array
            image_array = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            # Create a window using OpenCV and display the image with the audio file name as the title
            cv2.namedWindow(audio_file, cv2.WINDOW_NORMAL)
            cv2.imshow(audio_file, image_array)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return image_click_handler


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())