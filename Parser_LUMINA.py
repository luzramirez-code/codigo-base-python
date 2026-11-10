"""
PROYECTO LUMINA - ANALIZADOR SINTACTICO (PARSER)
Metodo: Analisis descendente recursivo (Recursive Descent Parser)

Alcance de este prototipo:
- Reconoce la sentencia de entrada: leer(identificador);
- Reconoce la sentencia de salida: mostrar(lista_salida);
- Permite concatenar expresiones con ++.
- Reconoce expresiones aritmeticas, relacionales y logicas.
- Usa un tokenizador sencillo para probar el Parser sin el Lexer definitivo.

IMPORTANTE:
Este archivo es un prototipo independiente. No sustituye al Lexer real de
LUMINA ni reconoce todavia la estructura completa "inicio ... fin".
"""

from dataclasses import dataclass
import re
from typing import List


# ---------------------------------------------------------------------
# 1. TOKENS
# ---------------------------------------------------------------------

@dataclass
class Token:
    tipo: str
    lexema: str
    posicion: int


PALABRAS_RESERVADAS = {
    "leer": "LEER",
    "mostrar": "MOSTRAR",
    "verdadero": "VERDADERO",
    "falso": "FALSO",
    "Y": "Y",
    "O": "O",
    "NO": "NO",
}

PATRON_TOKEN = re.compile(
    r'(?P<ESPACIO>\s+)'
    r'|(?P<CADENA>"(?:\\.|[^"\\])*")'
    r'|(?P<NUMERO>\d+(?:\.\d+)?)'
    r'|(?P<IDENTIFICADOR>[A-Za-z_][A-Za-z0-9_]*)'
    r'|(?P<OPERADOR>==|!=|<=|>=|\+\+|[+\-*/%<>])'
    r'|(?P<PARENTESIS>[()])'
    r'|(?P<PUNTO_COMA>;)'
)


def tokenizar(codigo: str) -> List[Token]:
    """Tokenizador de apoyo para las pruebas del Parser."""
    tokens = []
    posicion = 0

    while posicion < len(codigo):
        coincidencia = PATRON_TOKEN.match(codigo, posicion)
        if not coincidencia:
            fragmento = codigo[posicion:posicion + 15]
            raise SyntaxError(
                f"Caracter no reconocido en la posicion {posicion}: {fragmento!r}"
            )

        tipo = coincidencia.lastgroup
        lexema = coincidencia.group()
        inicio = posicion
        posicion = coincidencia.end()

        if tipo == "ESPACIO":
            continue
        elif tipo == "CADENA":
            tokens.append(Token("CADENA_LITERAL", lexema, inicio))
        elif tipo == "NUMERO":
            tokens.append(Token("NUMERO", lexema, inicio))
        elif tipo == "IDENTIFICADOR":
            tokens.append(Token(PALABRAS_RESERVADAS.get(lexema, "IDENTIFICADOR"),
                                lexema, inicio))
        elif tipo == "PARENTESIS":
            nombre = "PARENTESIS_ABRE" if lexema == "(" else "PARENTESIS_CIERRA"
            tokens.append(Token(nombre, lexema, inicio))
        elif tipo == "PUNTO_COMA":
            tokens.append(Token("PUNTO_COMA", lexema, inicio))
        elif tipo == "OPERADOR":
            operadores = {
                "++": "CONCATENAR",
                "+": "MAS",
                "-": "MENOS",
                "*": "MULTIPLICACION",
                "/": "DIVISION",
                "%": "MODULO",
                "==": "IGUAL",
                "!=": "DIFERENTE",
                "<": "MENOR",
                ">": "MAYOR",
                "<=": "MENOR_IGUAL",
                ">=": "MAYOR_IGUAL",
            }
            tokens.append(Token(operadores[lexema], lexema, inicio))

    tokens.append(Token("FIN_ARCHIVO", "", len(codigo)))
    return tokens


# ---------------------------------------------------------------------
# 2. ANALIZADOR SINTACTICO
# ---------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.posicion = 0

    def actual(self) -> Token:
        return self.tokens[self.posicion]

    def consumir(self, tipo_esperado: str) -> Token:
        token = self.actual()
        if token.tipo != tipo_esperado:
            self.error(f"se esperaba {tipo_esperado}")
        self.posicion += 1
        return token

    def error(self, mensaje: str = "estructura no valida"):
        token = self.actual()
        encontrado = token.lexema if token.lexema else "FIN_ARCHIVO"
        raise SyntaxError(
            f"Error sintactico en posicion {token.posicion}: {mensaje}; "
            f"se encontro {encontrado!r} ({token.tipo})."
        )

    def es_operador_relacional(self, tipo: str) -> bool:
        return tipo in {
            "IGUAL", "DIFERENTE", "MENOR", "MAYOR",
            "MENOR_IGUAL", "MAYOR_IGUAL"
        }

    # <identificador>
    def identificador(self):
        self.consumir("IDENTIFICADOR")

    # <sentencia_entrada> = leer ( identificador ) ;
    def sentencia_entrada(self):
        self.consumir("LEER")
        self.consumir("PARENTESIS_ABRE")
        self.identificador()
        self.consumir("PARENTESIS_CIERRA")
        self.consumir("PUNTO_COMA")

    # <sentencia_salida> = mostrar ( lista_salida ) ;
    def sentencia_salida(self):
        self.consumir("MOSTRAR")
        self.consumir("PARENTESIS_ABRE")
        self.lista_salida()
        self.consumir("PARENTESIS_CIERRA")
        self.consumir("PUNTO_COMA")

    # <lista_salida> = expresion { ++ expresion }
    def lista_salida(self):
        self.expresion()
        while self.actual().tipo == "CONCATENAR":
            self.consumir("CONCATENAR")
            self.expresion()

    # <expresion> = <expresion_logica>
    def expresion(self):
        self.expresion_logica()

    # <expresion_logica> = <conjuncion> { O <conjuncion> }
    def expresion_logica(self):
        self.conjuncion()
        while self.actual().tipo == "O":
            self.consumir("O")
            self.conjuncion()

    # <conjuncion> = <negacion> { Y <negacion> }
    def conjuncion(self):
        self.negacion()
        while self.actual().tipo == "Y":
            self.consumir("Y")
            self.negacion()

    # <negacion> = NO <negacion> | <relacional>
    def negacion(self):
        if self.actual().tipo == "NO":
            self.consumir("NO")
            self.negacion()
        else:
            self.relacional()

    # <relacional> = <aritmetica> [ operador_relacional <aritmetica> ]
    def relacional(self):
        self.aritmetica()
        if self.es_operador_relacional(self.actual().tipo):
            self.posicion += 1
            self.aritmetica()

    # <aritmetica> = <termino> { (+ | -) <termino> }
    def aritmetica(self):
        self.termino()
        while self.actual().tipo in {"MAS", "MENOS"}:
            self.posicion += 1
            self.termino()

    # <termino> = <factor> { (* | / | %) <factor> }
    def termino(self):
        self.factor()
        while self.actual().tipo in {
            "MULTIPLICACION", "DIVISION", "MODULO"
        }:
            self.posicion += 1
            self.factor()

    # <factor> = identificador | numero | cadena | booleano
    #          | ( expresion ) | + factor | - factor
    def factor(self):
        tipo = self.actual().tipo

        if tipo in {
            "IDENTIFICADOR", "NUMERO", "CADENA_LITERAL",
            "VERDADERO", "FALSO"
        }:
            self.posicion += 1
        elif tipo == "PARENTESIS_ABRE":
            self.consumir("PARENTESIS_ABRE")
            self.expresion()
            self.consumir("PARENTESIS_CIERRA")
        elif tipo in {"MAS", "MENOS"}:
            self.posicion += 1
            self.factor()
        else:
            self.error("se esperaba un identificador, numero, cadena, "
                       "booleano o expresion entre parentesis")

    # <sentencia> = <sentencia_entrada> | <sentencia_salida>
    def sentencia(self):
        if self.actual().tipo == "LEER":
            self.sentencia_entrada()
        elif self.actual().tipo == "MOSTRAR":
            self.sentencia_salida()
        else:
            self.error("se esperaba una sentencia LEER o MOSTRAR")

    # Analiza una o varias sentencias hasta FIN_ARCHIVO.
    def analizar(self):
        if self.actual().tipo == "FIN_ARCHIVO":
            self.error("el archivo no contiene sentencias")

        while self.actual().tipo != "FIN_ARCHIVO":
            self.sentencia()

        self.consumir("FIN_ARCHIVO")
        return True


# ---------------------------------------------------------------------
# 3. FUNCION DE PRUEBA
# ---------------------------------------------------------------------

def analizar_codigo(codigo: str) -> bool:
    """Tokeniza y analiza el codigo. Devuelve True si la sintaxis es correcta."""
    tokens = tokenizar(codigo)
    parser = Parser(tokens)
    return parser.analizar()


def ejecutar_pruebas():
    pruebas = [
        ("leer(edad);", True),
        ('mostrar("Hola mundo" ++ edad);', True),
        ('mostrar("Edad: " ++ edad);', True),
        ("mostrar(edad * 2);", True),
        ("mostrar(edad > 18 Y verdadero);", True),
        ("leer(25);", False),
        ("leer(edad;", False),
        ("mostrar(\"Hola\" ++);", False),
    ]

    print("PRUEBAS DEL ANALIZADOR SINTACTICO LUMINA")
    print("-" * 55)

    for codigo, se_espera_correcto in pruebas:
        try:
            analizar_codigo(codigo)
            correcto = True
            detalle = "Sintaxis correcta"
        except SyntaxError as error:
            correcto = False
            detalle = str(error)

        estado = "ACEPTADA" if correcto else "RECHAZADA"
        resultado = "OK" if correcto == se_espera_correcto else "ERROR DE PRUEBA"
        print(f"{estado:10} | {codigo:38} | {resultado}")
        if not correcto:
            print(f"           Detalle: {detalle}")


if __name__ == "__main__":
    ejecutar_pruebas()
