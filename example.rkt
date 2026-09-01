#lang roulette/example/probalog

% LIBRARY FUNCTIONS
IsZero("0").
Succ("0", "1").
Succ("1", "2").
Succ("2", "3").
Succ("3", "4").
Succ("4", "5").
Succ("5", "6").
Succ("6", "7").
Succ("7", "8").
Succ("8", "9").
Succ("9", "10").
Succ("10", "11").
Succ("11", "12").
Succ("12", "13").
Succ("13", "14").
Succ("14", "15").
Succ("15", "16").
Succ("16", "17").
Succ("17", "18").
Succ("18", "19").
Succ("19", "20").
Succ("20", "21").
Succ("21", "22").

IsLt(a, b) :- Succ(a, b).
IsLt(a, b) :- IsLt(a, c), Succ(c, b).

% LLM PROMPT BELOW
