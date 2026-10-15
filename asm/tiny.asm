; Runtime tiny text for item-name lists (build.py patch_tiny assembles this with asar).
; Two 3x5 letters per 8-px cell, drawn into the top tile of the cell (bottom = blank tile $3FF). Cells get BG3
; page-0 tiles from a pool (font.TINY_POOL); their pixels go to a WRAM mirror, uploaded by the NMI hook.
; Defines from build.py: CODE, POOL_T0 (first pool tile), POOL_N (slots), DICT_READ, TINY_FONT (8 bytes per code
; from $100: rows 0-5, pixels in the high nibble, byte 6 = 1 when the glyph exists), TINY_N (codes in TINY_FONT).
lorom

!MIRROR = $7FD000   ; POOL_N tiles of 16 bytes (7F:D000-FABF is never written by the game, tools/lua/wramuse.lua)
!OWNER = $7FDE40    ; per slot: tilemap buffer offset that shows it, $FFFF = none
!MAGIC = $7FE010
!NEXT = $7FE012     ; next slot to try
!DLO = $7FE014      ; dirty slots [DLO, DHI) to upload; DHI = 0: nothing
!DHI = $7FE016
!PEND = $7FE018     ; font offset of a left letter waiting for its right neighbour, $FFFF = none
!CUR = $7FE01A
!LOFF = $7FE01C
!ROFF = $7FE01E
!MOFF = $7FE020
!TMP = $7FE022
!TRIES = $7FE024
!SLOT = $7FE026
!KEY = $7A31
!CAP = $0060        ; slots uploaded per frame (16 bytes each)

assert !POOL_N*16 <= $0E40

org !CODE
; --- entries (JSL; X = word pointer for DICT_READ, Y = offset into the tilemap buffer $2780; Y returns past the
; --- last cell like the per-glyph loops it replaces)
tiny71d:            ; loops that drew with JSR $B71D: attribute $1C00
    PHP
    REP #$30
    PHA
    LDA #$1C00
    STA $0709
    PLA
    PLP
tiny725:            ; loops that drew with JSR $B725: attribute already in $0709
    PHP
    REP #$30
    LDA $060C
    AND #$00FF
    CMP #$0005
    BCC .tiny
.plain:             ; other screen modes (battle): the original per-glyph drawing
    JSL !DICT_READ
    PHA
    PHX
    AND #$7FFF
    JSR draw_glyph
    PLX
    PLA
    BMI .done
    INX
    INX
    BRA .plain
.done:
    PLP
    RTL
.tiny:
    JSR init
    LDA #$FFFF
    STA.l !PEND
.loop:
    JSL !DICT_READ
    STA.l !CUR
    PHX
    AND #$7FFF
    JSR tiny_index
    BCC .other
    TAX
    LDA.l !PEND
    BMI .first
    JSR emit
    LDA #$FFFF
    STA.l !PEND
    BRA .next
.first:
    TXA
    STA.l !PEND
    BRA .next
.other:             ; icon or a glyph the tiny font lacks: full-size cell
    PHA
    JSR flush
    PLA
    JSR draw_glyph
.next:
    PLX
    LDA.l !CUR
    BMI .end
    INX
    INX
    BRA .loop
.end:
    JSR flush
    PLP
    RTL

tiny_item:          ; 04:B65A: X = item number * 2
    LDA $2FA74F,x
    TAX
    JMP tiny71d

; A = glyph code -> carry set and A = offset into TINY_FONT, or carry clear and A unchanged
tiny_index:
    CMP #$02FF
    BEQ .space
    CMP #$0100
    BCC .no
    CMP.w #$0100+!TINY_N
    BCS .no
    STA.l !TMP
    SEC
    SBC #$0100
    ASL
    ASL
    ASL
    TAX
    LDA.l !TINY_FONT+6,x
    AND #$00FF
    BEQ .absent
    TXA
    SEC
    RTS
.absent:
    LDA.l !TMP
.no:
    CLC
    RTS
.space:
    LDA #$0000
    SEC
    RTS

flush:              ; a waiting left letter gets a blank right half
    LDA.l !PEND
    BMI .none
    LDX #$0000
    JSR emit
    LDA #$FFFF
    STA.l !PEND
.none:
    RTS

; A = left letter's font offset, X = right letter's: render one cell into a pool slot, store it at Y
emit:
    STA.l !LOFF
    TXA
    STA.l !ROFF
    JSR alloc
    LDA.l !MOFF
    TAX
    LDA #$FFFF      ; rows 0-1: background (colour 3: both planes set)
    STA.l !MIRROR,x
    STA.l !MIRROR+2,x
    PHY
    LDY #$0000
.row:               ; rows 2-7 = glyph rows 0-5: plane 0 all set, plane 1 clear where there is ink (colour 1)
    TYA
    CLC
    ADC.l !ROFF
    TAX
    LDA.l !TINY_FONT,x
    AND #$00F0
    LSR
    LSR
    LSR
    LSR
    STA.l !TMP
    TYA
    CLC
    ADC.l !LOFF
    TAX
    LDA.l !TINY_FONT,x
    AND #$00F0
    ORA.l !TMP
    EOR #$00FF
    XBA
    ORA #$00FF
    PHA
    TYA
    ASL
    CLC
    ADC.l !MOFF
    TAX
    PLA
    STA.l !MIRROR+4,x
    INY
    CPY #$0006
    BNE .row
    PLY
    LDA.l !SLOT
    CLC
    ADC.w #!POOL_T0
    ORA #$2C00      ; what 00:BA9D gives a glyph tile
    STA $0800
    LDA #$2FFF      ; blank tile $3FF
    STA $0802
    JMP store

; -> SLOT, MOFF = SLOT*16; OWNER[SLOT] = Y. Next fit from NEXT, skipping slots the tilemap buffer still shows.
alloc:
    LDA.w #!POOL_N
    STA.l !TRIES
.try:
    LDA.l !NEXT
    ASL
    TAX
    LDA.l !OWNER,x
    CMP #$FFFF
    BEQ .take
    TAX
    LDA $2780,x
    AND #$03FF
    STA.l !TMP
    LDA.l !NEXT
    CLC
    ADC.w #!POOL_T0
    CMP.l !TMP
    BNE .take
    JSR .advance
    LDA.l !TRIES
    DEC
    STA.l !TRIES
    BNE .try
.take:              ; (all slots on screen: the pool is too small for this screen; reuse the oldest)
    LDA.l !NEXT
    STA.l !SLOT
    ASL
    TAX
    TYA
    STA.l !OWNER,x
    LDA.l !SLOT
    ASL
    ASL
    ASL
    ASL
    STA.l !MOFF
    JSR .advance
    LDA.l !DHI
    BEQ .first
    LDA.l !SLOT
    CMP.l !DLO
    BCS +
    STA.l !DLO
+:
    INC
    CMP.l !DHI
    BCC +
    STA.l !DHI
+:
    RTS
.first:
    LDA.l !SLOT
    STA.l !DLO
    INC
    STA.l !DHI
    RTS
.advance:
    LDA.l !NEXT
    INC
    CMP.w #!POOL_N
    BCC +
    LDA #$0000
+:
    STA.l !NEXT
    RTS

init:
    LDA.l !MAGIC
    CMP #!KEY
    BEQ .ok
    PHX
    LDX.w #(!POOL_N-1)*2
    LDA #$FFFF
-:
    STA.l !OWNER,x
    DEX
    DEX
    BPL -
    LDA #$0000
    STA.l !NEXT
    STA.l !DHI
    LDA #!KEY
    STA.l !MAGIC
    PLX
.ok:
    RTS

draw_glyph:         ; A = glyph code: what 04:B725 does
    PHY
    JSL $00BA9D
    PLY
store:              ; $0800/$0802 -> tilemap buffer at Y (04:B72D)
    LDA $060C
    AND #$00FF
    CMP #$0006
    BNE .attr
    LDA $0800
    STA $2780,y
    LDA $0802
    STA $27C0,y
    INY
    INY
    RTS
.attr:
    LDA $0802
    AND #$C3FF
    ORA $0709
    STA $27C0,y
    LDA $0800
    AND #$C3FF
    ORA $0709
    STA $2780,y
    INY
    INY
    RTS

; --- NMI, frame-ready branch (00:82A8, replaces LDA #$80 ; STA $2115; 8-bit A/X, DB = 0): upload dirty slots
nmi_upload:
    PHP
    REP #$30
    LDA.l !MAGIC
    CMP #!KEY
    BNE .skip
    LDA.l !DHI
    BNE .go
.skip:
    JMP .out
.go:
    SEC
    SBC.l !DLO
    CMP.w #!CAP+1
    BCC +
    LDA.w #!CAP
+:
    STA.l !TMP
    LDA.l !DLO
    CLC
    ADC.w #!POOL_T0
    ASL
    ASL
    ASL
    CLC
    ADC #$6000      ; BG3 tiles at VRAM word $6000
    STA $2116
    LDA.l !DLO
    ASL
    ASL
    ASL
    ASL
    CLC
    ADC #!MIRROR&$FFFF
    STA $4372
    LDA.l !TMP
    ASL
    ASL
    ASL
    ASL
    STA $4375
    SEP #$20
    LDA $1B0D       ; channel 7 off as HDMA first (as 00:8374 does right after)
    AND #$7F
    STA $1B0D
    STA $420C
    LDA #$80
    STA $2115
    LDA #$01
    STA $4370
    LDA #$18
    STA $4371
    LDA #!MIRROR>>16
    STA $4374
    LDA #$80
    STA $420B
    REP #$20
    LDA.l !DLO
    CLC
    ADC.l !TMP
    STA.l !DLO
    CMP.l !DHI
    BCC .out
    LDA #$0000
    STA.l !DHI
.out:
    SEP #$20
    LDA #$80
    STA $2115
    PLP
    RTL

; --- font loader 00:B7F6 (replaces its first JSL $008E1E; Y = VRAM destination): the reload wipes page 0, so
; --- upload every slot again
font_reload:
    PHP
    REP #$30
    PHA
    CPY #$6000
    BNE +
    LDA.l !MAGIC
    CMP #!KEY
    BNE +
    LDA #$0000
    STA.l !DLO
    LDA.w #!POOL_N
    STA.l !DHI
+:
    PLA
    PLP
    JML $008E1E

print "tiny71d=", hex(tiny71d)
print "tiny725=", hex(tiny725)
print "tiny_item=", hex(tiny_item)
print "nmi_upload=", hex(nmi_upload)
print "font_reload=", hex(font_reload)
print "end=", hex(pc())
