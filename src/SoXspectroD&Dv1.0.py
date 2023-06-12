import sys, subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtGui import QIcon, QImage, QPixmap, QCursor
from PyQt5.QtCore import Qt, QMimeData, QFileInfo
import os.path as op, os, io
from PyQt5.QtWidgets import QFileIconProvider,QScrollArea
import winsound
from pydub import AudioSegment
import cv2
import numpy as np

WINDOW_TITLE = "SoXspectroD&D"

MAINWIN_W = 1280
MAINWIN_H = 720
filelistH = 300

AUDIO_FORMATS = ('.flac', '.wav', '.mp3', '.ogg') # list of file extentions to be parsed

SoXSpectroW = 800 #default 800
SoXSpectroH = 256 # for one channel

SoXPath = 'sox' # path to the sox / use 'sox' if SoX is in path environment variable

DO_SAVE_TO_SUBFOLDER = True # whether to save the spectrograms to a subfolder. They will be saved RELATIVE TO THEIR RESPECTIVE AUDIO FILES
SUBFOLDER_NAME = "Spectrograms"

# test if sox is installed
try:
    subprocess.check_output([SoXPath, '--version'])
except (subprocess.CalledProcessError, FileNotFoundError):
    raise FileNotFoundError("SoX may not be installed. Please set the path to sox.exe in the settings")

class FileDropWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, MAINWIN_W, MAINWIN_H)  # Geometry   
        self.setAcceptDrops(True)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setFixedHeight(filelistH)  # Set fixed height for the file view
        self.tree_widget.setHeaderHidden(False)
        self.tree_widget.setHeaderLabel("Audio files")
        #self.folder_view_left.header().resizeSection(0, folder_viewW)  # Adjust width of the first section (Name)

        self.clear_button = QPushButton("Clear file list")
        self.clear_button.clicked.connect(self.clear_file_paths)
        
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
        layout.addWidget(self.tree_widget)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.process_button)
        layout.addWidget(self.save_button)
        layout.addWidget(self.scroll_area)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        self.resizeEvent(None)
        self.images = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile().replace("\\","/")
            self.add_file_item(file_path)
        if self.tree_widget.topLevelItemCount() > 0 :
            self.process_button.setEnabled(True)
            self.process_button.setText("Process Audio (" + str(self.tree_widget.topLevelItemCount()) + " files)" )
        else:
            self.process_button.setEnabled(False)
            self.process_button.setText("Process Audio")

    def add_file_item(self, file_path):
        file_extension = op.splitext(file_path)[1].lower()
        if file_extension in AUDIO_FORMATS:
            file_icon = self.get_file_icon(file_path)
            item = QTreeWidgetItem([file_path])
            item.setIcon(0, file_icon)
            if not ( self.tree_widget.findItems(file_path, Qt.MatchFixedString) ): self.tree_widget.addTopLevelItem(item) # add item if not already present

    def get_file_icon(self, file_path):
        file_info = QFileInfo(file_path)
        icon_provider = QFileIconProvider()
        file_icon = icon_provider.icon(file_info)

        return file_icon

    def clear_file_paths(self):
        self.tree_widget.clear()
        self.process_button.setEnabled(False)
        self.process_button.setText("Process Audio")
            
    def process_audio(self):
        if self.tree_widget.topLevelItemCount() == 0:
            return # do nothing if there is no audio files
        
        audio_files = [item.text(0) for item in self.get_all_items(self.tree_widget)] # list all items

        total_files = len(audio_files)
        processed_files = 0

        # Clear the previous images from the scrollable layout and the images list
        self.clear_images()
        self.images = []

        for audio_file in audio_files:
            # showing progress
            processed_files += 1
            file_path = op.abspath(audio_file).replace("\\","/")
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
            self.images.append((result, audio_file))

        self.setWindowTitle(WINDOW_TITLE)
        if self.images:
            self.save_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)
        print("Processing done")
            
    def get_all_items(self,tree_widget):
        # Retrives the list of all files in the tree
        all_items = []

        # Get the root item
        root_item = tree_widget.invisibleRootItem()

        # Recursively traverse the tree
        self.traverse_tree(root_item, all_items)

        return all_items[1:] #remove the first

    def traverse_tree(self,item, all_items):
        # Add the current item to the list
        all_items.append(item)

        # Recursively traverse the child items
        for i in range(item.childCount()):
            child_item = item.child(i)
            self.traverse_tree(child_item, all_items)

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
            
            
    def save_images(self):
        for image_data, audio_file in self.images:
            if (DO_SAVE_TO_SUBFOLDER): #saving to a subfolder
                os.mkdir( op.join(op.dirname(audio_file), SUBFOLDER_NAME) ) # creating the corresponding subfolder
                file_path = op.join(op.join(op.dirname(audio_file), SUBFOLDER_NAME), op.basename(audio_file) + ".png") # saving to the subfolder
            else:
                file_path = op.join(audio_file + ".png")
            with open(file_path, "wb") as file:
                print("Writing image... " + file_path)
                file.write(image_data)
        print("Images saved successfully!")
        self.play_complete_sound()
        
    def play_complete_sound(self):
        winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)

    def clear_images(self):
        # Clear the scrollable layout
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        # Clear the images list
        self.images.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileDropWindow()
    window.show()
    sys.exit(app.exec_())
