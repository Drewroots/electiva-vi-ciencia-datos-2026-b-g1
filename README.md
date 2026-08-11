# Electiva VI - Ciencia de Datos - 2026-B

Repositorio de clase - Corporacion Universitaria del Huila (CORHUILA).

| | |
| --- | --- |
| **Grupo** | Ciencia de Datos |
| **Horario** | Sabado 6:00 a. m. - 7:40 a. m. |
| **Aula** | C4-409 |
| **Semestre** | 2026-B |

## Estructura

Cada `NN-week/` contiene:

```
NN-week/
|-- 01-session/   # material de clase del docente (sesion 1)
|-- 02-session/   # material de clase del docente (sesion 2)
\-- hu-status/    # tu entrega de la semana (en tu fork)
```

No borres `01-session` / `02-session`: el docente sube ahi el material de clase, y
mantenerlas estables evita conflictos cuando actualices tu fork.

## Como entregar
Coloca tu entrega en `NN-week/hu-status/` de tu **fork**. Ten tu **repo de perfil**
`usuario/usuario` con el bloque CONFIG:

```
<!-- CONFIG
FULL_NAME: Tu Nombre Completo
GITHUB_USER: tu-usuario
-->
```

```bash
git clone https://github.com/<tu-usuario>/electiva-vi-ciencia-datos-2026-b-g1.git
cd electiva-vi-ciencia-datos-2026-b-g1
# edita NN-week/hu-status/README.md o agrega tus archivos ahi
git add . && git commit -m "Entrega semana NN" && git push
```

Material interactivo (OVAs): https://code-corhuila.github.io/ova-web/2026-B/ciencia-datos/
Guia de entrega (PDF): https://code-corhuila.github.io/ova-web/manuales/Manual-Entrega-GitHub.pdf
