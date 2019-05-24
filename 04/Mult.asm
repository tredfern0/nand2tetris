// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Put your code here.

//Generally - R0+R0 R1 times.  Subtract 1 from R1 each time, exit loop when it's done

//Initialize R2 to 0, this is where we'll hold the calculation
  @R2
  M=0

//If R1==0, jump to end
  @R1
  D=M
  @INFINITE_LOOP
  D;JEQ

//If R1>0, jump to increment loop
  @INCREMENT_LOOP
  D;JGT

//Otherwise, it's less than 0, invert both R0 and R1, continue
  @R0
  M=-M
  @R1
  M=-M

//Loop around and add R0 to R2, R1 times
(INCREMENT_LOOP)
  @R0
  D=M
  @R2
  M=D+M
  @R1
  M=M-1
  D=M
@INCREMENT_LOOP  // Check for jump condition
  D;JGT

(INFINITE_LOOP)
   @INFINITE_LOOP
   0;JMP            // infinite loop

