// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed.
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Put your code here.

(KEYBOARD_CHECK)
  @24576
  D=M  //Store the keyboard value in D
  @SET_BLACK  //If it's NOT ZERO, jump to set black, else jump to set white
  D;JNE

(SET_WHITE)
  @R1
  M=0
  @UPDATE_SCREEN
  0;JEQ

(SET_BLACK)  //Set R1 to -1 and call update screen func
  @R1
  M=-1
  @UPDATE_SCREEN
  0;JEQ

(UPDATE_SCREEN)
  @SCREEN
  D=A  //Sets the D(ata) register to 16384
  @R0
  M=D  //Stores 16384 in R0

(BLACK_LOOP)  //Increment by 1 until we reach our value
  //What we want to do - write M[16384]=-1
  //Increment R0 to be 16385
  //Set incremented R0 to be value

  @R1  //So we can store 0 or -1 in R1, and update screen to that value
  D=M

  @R0
  A=M  //Address = 16384 now
  M=D  //Set M[16384]=-1

  @R0
  M=M+1  //Increment our current address value

  //Need to compare M to 24575 - cut off higher for it to work
  @24576
  D=A
  @R0
  D=D-M

@BLACK_LOOP  //Loop back around
  D;JGT

@KEYBOARD_CHECK
  0;JMP            // infinite loop

