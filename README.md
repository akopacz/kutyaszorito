# Kutyaszorító

Futtatás: 

```sh
python3 arena.py
```
# Kutyaszorító - Kommunikációs protokoll

A két kliens a 'localhost' 10000 portra kell csatlakozzon ahhoz, hogy tudjanak kommunikálni a szerverrel.

# Kommunikációs protokoll

Valósítsunk meg egy klienst úgy, hogy a bot játékos tudjon csatlakozni egy szerverhez socketen keresztül és JSON formátumú üzenetekkel kommunikáljon vele. A kliens több játékot (kört) kell tudjon játszani egy másik (bot) játékos ellen egy K*K méretű pályán. A pálya sorai, illetve oszlopai 0-tól (K - 1)-ig vannak számozva.

A kliens a localhost:10000 címre kell csatlakozzon (tcp kapcsolattal). A sikeres csatlakozás esetén a szerver küld egy 
inicializációs üzenetet, amelyben szerepel a pálya mérete, és az éppen csatlakozó játékos sorszáma. A játékosok lehetséges sorszámai: 1 vagy 2. 
Az üzenet struktúrája a következő:
```jsonc
{
    "cmd": "init",
    "K": <pálya mérete>, 
    "id": <játékos id-ja>
}
```
Példa: `{"cmd": "init", "K": 7, "id": 2}`

A kliens jelzi, hogy megkapta az üzenetet:
```jsonc
{
    "status": "OK"
}
```

Minden új kör elején a szerver küld egy "start" üzenetet, a játékosok kezdő pozícióival:
```jsonc
{
    "cmd": "start",
    "coords": [<x1>, <y1>],    // az aktuális játékos koordinátája 
    "op_coords": [<x2>, <y2>]  // az ellenfél játékos koordinátája 
}
```
Példa: `{"cmd": "start", "coords": [0, 2], "op_coords": [4, 2]}`

Ez az üzenet jelzi, hogy egy új kör kezdődött, a szerver nem küld egy külön üzenetet, hogy befejeződött az előző kör. 
A kliens ebben az esetben is jelzi, hogy megkapta az üzenetet:
```jsonc
{
    "status": "OK"
}
```

Amikor a kliens kell lépjen, akkor ezt a szerver jelzi egy üzenettel, amelyben szerepel az ellenfél előző lépése is. Ha ez az első lépés, azaz az ellenfélnek nem volt még előző lépése, akkor a "move" és "exclude" mezők null-t tartalmaznak.
```jsonc
{
    "cmd": "move",
    "move": [<x1>, <y1>],
    "exclude": [<x2>, <y2>]
}
```
Példa: `{"cmd": "move", "move": [1, 3], "exclude": [4, 1]}`

A kliens ezután válaszol egy hasonló json objektummal, amiben jelzi az ő lépését a `"move"` és `"exclude"` mezőkkel:
```jsonc
{
    "move": [<x1>, <y1>],
    "exclude": [<x2>, <y2>]
}
```
Példa: `{"move": [2, 2], "exclude": [4, 4]}`

Amiután az összes játszma véget ért, ezt az üzenetet kapják a játékosok:
```jsonc 
{
    "cmd": "over",
    "winner": <játékos id> // null-t tartalmaz döntetlen esetén
}
```

## Hiba kezelés: 

Amikor a kliens nem megfelelő mezőre akar lépni, vagy olyan mezőt akar kizárni, amelyet nem lehet, akkor a szerver mindkét 
játékosnak üzenetet küld. Amikor a játékos hibás mezőre akar lépni, vagy hibás mezőt akar kizárni, akkor automatikusan 
elveszíti azt a kört és új játék kezdődik.
```jsonc
{
    "cmd": "error",
    "msg": <üzenet>,        // a hibát leiró specifikusabb üzenet
    "id": <játékos id>      // az a játékos, aki hibás mezőt jelölt meg
}
```
Példa: `{"cmd": "error", "msg": "invalid input", "id": 1}`

Hogyha a kliens futása során valamilyen hiba (exception) lép fel, akkor küldjön egy üzenetet, amelyben szerepel a `"client_error"` mező.

Példa:
```jsonc
{
    "client_error": true,
    "msg":  <üzenet>
}
```