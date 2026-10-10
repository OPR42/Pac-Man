# Acceptance test plan

## Summary

1. [Launch](#1-launch)
2. [Maze generation](#2-maze-generation)
3. [Player](#3-player)
4. [Ghosts](#4-ghosts)
5. [Pacgums and Super-pacgums](#5-pacgums-and-super-pacgums)
6. [Cheat mode](#6-cheat-mode)
7. [Scoring](#7-scoring)
8. [Game progression](#8-game-progression)
9. [User interface](#9-user-interface)
10. [General operation](#10-general-operation)
11. [Bugs fixed](#11-bugs-fixed)

## 1. Launch

|Test performed|Command|Result||
|---|---|---|---|
|Normal launch|`python3 pac-man.py data/config.json`|Game launches -> main menu|☑️❌|
|No config file|`python3 pac-man.py`|Game launches with default values|☑️❌|
|Too many arguments|`python3 pac-man.py test.json test2.json`|Extra arguments are ignored|☑️❌|
|Non-existent config file|`python3 pac-man nothing.json`|Game launches with default values|☑️❌|
|Permission denied on config file|`python3 pac-man.py data/config.json`|Game launches with default values|☑️❌|
|Non-json config file|`python3 pac-man some_file.txt`|Game launches with default values|☑️❌|

## 2. Level generation

|Test performed|Result||
|---|---|---|
|Fixed seed for level 1|The first level is always the same|☑️❌|
|Random seed for next levels|Levels after 1 are randomly generated|☑️❌|
|Configurable size|The maze takes on the indicated dimensions|☑️❌|
|Flag `Perfect=False`|The maze contains loops and is Pac-man-compatible|☑️❌|
|Failed generation|[...]|☑️❌|


## 3. Player

|Test performed|Action|Result||
|---|---|---|---|
|Collision|Move towards a wall|Pac-man stops|☑️❌|
|Move up|Press < up_key >|Pac-man moves upwards if he does not encounter a wall.|☑️❌|
|Move down|Press < down_key >|Pac-man moves downwards if he does not encounter a wall.|☑️❌|
|Move right|Press < right_key >|Pac-man moves to the right if he does not encounter a wall.|☑️❌|
|Move left|Press < left_key >|Pac-man moves to the left if he does not encounter a wall.|☑️❌|
|Contact with a ghost|Move onto a ghost|Pac-man loses a life and reappears in the center.|☑️❌|
|Last life loss|Move onto a ghost|Game ends|☑️❌|


## 4. Ghosts

|Test performed|Action|Result||
|---|---|---|---|
|Non-edible ghost|Auto|Chases the player|☑️❌|
|Edible ghost|Auto|Runs away from the player|☑️❌|
|Disgusted ghost|Use sage|Flees from the player within a certain radius|☑️❌|
|Contact with Pac-man (non-edible)|Move onto a ghost|Eats Pac-man and continues on its way|☑️❌|
|Contact with Pac-man (edible)|Move onto a ghost|Is eaten, respawns in its corner|☑️❌|

## 5. Pacgums and Super-pacgums

|Test performed|Action|Result||
|---|---|---|---|
|Eat a pacgum|Move onto a pacgum|Score increased by [...] points|☑️❌|
|Eat a super-pacgum|Move onto a super-pacgum|Score increased by [...] points, makes ghosts edible|☑️❌|

## 6. Cheat mode

<span style='color: purple'>

### Persistent cheats
</span>

|Test performed|Result||
|---|---|---|
|Invulnerable|Harmless ghosts|☑️❌|
|Sprinter|Doubles movement speed|☑️❌|
|Out A Time|Freezes time and ghosts|☑️❌|
|Wall Denier|Ignores obstacles|☑️❌|
|Jack Hammer|Destructs obstacles|☑️❌|
|Gum Charmer|Attracts pacgums|☑️❌|
|Gluttonous|Vulnerable ghosts|☑️❌|

<span style='color:purple'>

### One-time cheats
</span>

|Test performed|Result||
|---|---|---|
|Add 10 lives|Adds 10 lives. Right-click removes 10 lives|☑️❌|
|Add 10,000 points|Adds 10,000 points. Right-click removes 10,000 points|☑️❌|
|Reset time|Restores remaining time to its initial value. Right-click sets it to 10 seconds|☑️❌|
|Phase out ghosts|Ghosts become ethereal. Right-click to cancel|☑️❌|
|Reset current level|Resets this level to its original state.|☑️❌|
|Advance to next level|Completes this level and starts the next one. Right-click to return to the previous level|☑️❌|
|Fill inventory|Adds each item type to the inventory. Right-click to empty it|☑️❌|

## 7. Scoring

|Test performed|Result||
|---|---|---|
|Eat a pacgum|Score increased by 10 points|☑️❌|
|Eat a super-pacgum|Score increased by 50 points|☑️❌|
|Eat an edible ghost|Score increased by 200 points|☑️❌|
|Take a crate|Score increased by X points|☑️❌|
|Finish a level with time left|Score increased by X points / second left|☑️❌|
|Finish the game with lives left|Score increases by one-fifth of the points required to earn a life for each remaining life.|☑️❌|
|Decrease the score|No action can decrease the score|☑️❌|

## 8. Game progression

<span style='color: purple'>

### Global
</span>

|Test performed|Result||
|---|---|---|
|Reach the time limit for a level|Depends on the configuration *|☑️❌|
|Complete a level|Move to the next level|☑️❌|
|Complete all levels|No crash observed|☑️❌|
|Complete the final level|Game ends|☑️❌|
|Pause the game|Opens pause menu to access several options|☑️❌|
|Game ends (win or lose)|Final score is displayed|☑️❌|

<i>
* Reaching the time limit can either:  

- Double the ghosts' movement speed
- Remove 1 life
- Trigger a "Game over"
- Kill Pacman
</i>

<span style='color: purple'>

### Level completion
</span>

|Test performed|Result||
|---|---|---|
|Score retained between levels|Score for level N is displayed at level N+1|☑️❌|
|Lives retained between levels|Remaining lives for level N are displayed at level N+1|☑️❌|

## 9. User interface

<span style='color: purple'>

### Main menu
</span>

|Test performed|Result||
|---|---|---|
|Start game|[...]|☑️❌|
|View highscores|[...]|☑️❌|
|Instructions|[...]|☑️❌|
|Exit|[...]|☑️❌|

<span style='color: purple'>

### In-game HUD
</span>

|Test performed|Result||
|---|---|---|
|Current score|[...]|☑️❌|
|Remaining lives|[...]|☑️❌|
|Current level|[...]|☑️❌|
|Remaining time|[...]|☑️❌|
|Inventory|||

<span style='color: purple'>

### Pause menu
</span>

|Test performed|Result||
|---|---|---|
|Resume|[...]|☑️❌|
|Back to main menu|[...]|☑️❌|
|Settings|||
|Cheats|||
|Exit|||

<span style='color: purple'>

### Game Over screen
</span>

|Test performed|Result||
|---|---|---|
|Final score display|[...]|☑️❌|
|Enter name|[...]|☑️❌|

<span style='color: purple'>

### Victory screen
</span>

|Test performed|Result||
|---|---|---|
|Final score display|[...]|☑️❌|
|Enter name|[...]|☑️❌|

## 10. General operation

|Test performed|Result||
|---|---|---|
|Norm|No flake8 or mypy errors|☑️❌|
|No crashes|All errors are catched and displayed|☑️❌

## 11. Bugs fixed

<span style='color: goldenrod'>

### ⚠️ Launch
</span>

- Game does not launch if it has not been installed beforehand.  
↳ Issue: Crash

- Mazegenerator not found if the game is launched outside of its virtual environment.  
↳ Issue: Crash

- If the audio device does not start correctly, the music tracks reload continuously.  
↳ Issue: Slowdowns during gameplay, making it nearly impossible to play


<span style='color: goldenrod'>

### ⚠️ Banner
</span>

- Disabling the banner does not remove it, but simply makes it invisible.  
↳ Issue: An unwanted collision in the main menu

- If the theme is changed during the game, the banner does not reset at the end of the game.  
↳ Issue: The banner keeps the last theme used


<span style='color: goldenrod'>

### ⚠️ Game
</span>

- In point-and-click mode, when clicking on a blocked tile, Pacman always targets the nearest tile in a clockwise direction (1st up, 2nd right, etc.)  
↳ Issue: Pacman should target a tile based on the section of the clicked square.

- Cheat menu is accessible even when not visible.  
↳ Issue: Not a big deal, but still a bit strange.

- After winning, the player cannot return to the main menu after entering their name.  
↳ Issue: The player is forced to restart the game to play another round. 


<span style='color: goldenrod'>

### ⚠️ Sidebars
</span>

- Metallic textures do not display the same on different devices.  
↳ Issue: Lack of lisibility
