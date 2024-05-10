# Hideandseek

Two devices. One gets hidden the other device seeks it

Hider - Raspberry Pi 4, GPS, battery, project box
  Sends its coordinates to the seekr via wifi, coordinates are x and y, 12345 67890

Seeker - Raspberry Pi Zero 2 w, GPS, battery, project box
  Recieves XY from Hider via wifi, calculates the distance between the hider and itself and beeps according, similiar to a metal detector


Using two five digit XY coordinates instead of lat/long will allow the addition of the decawave system in the future
