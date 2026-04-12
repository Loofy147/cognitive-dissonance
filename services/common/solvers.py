import re
from itertools import combinations, product

import numpy as np

# Expanded Wonderland dictionary for better text decoding coverage
WONDERLAND_WORDS = [
    "above",
    "alice",
    "ancient",
    "around",
    "beyond",
    "bird",
    "book",
    "bright",
    "castle",
    "cat",
    "cave",
    "chases",
    "clever",
    "colorful",
    "creates",
    "curious",
    "dark",
    "deep",
    "discovers",
    "door",
    "dragon",
    "dream",
    "eagle",
    "elf",
    "enchanted",
    "enters",
    "explores",
    "finds",
    "follows",
    "forest",
    "found",
    "fountain",
    "friend",
    "garden",
    "giant",
    "glass",
    "gold",
    "green",
    "hidden",
    "imagines",
    "in",
    "inside",
    "island",
    "key",
    "king",
    "knight",
    "library",
    "magical",
    "map",
    "message",
    "mirror",
    "mountain",
    "mouse",
    "mysterious",
    "near",
    "ocean",
    "palace",
    "potion",
    "princess",
    "puzzle",
    "queen",
    "rabbit",
    "reads",
    "school",
    "secret",
    "sees",
    "silver",
    "story",
    "strange",
    "student",
    "studies",
    "teacher",
    "the",
    "through",
    "tower",
    "treasure",
    "turtle",
    "under",
    "valley",
    "village",
    "watches",
    "wise",
    "wizard",
    "wonderland",
    "writes",
    "draws",
    "dreams",
    "hatter",
    "golden",
    "crystal",
    "shiny",
    "diamond",
    "ruby",
    "emerald",
    "sapphire",
    "pearl",
    "locket",
    "white",
    "rabbit",
]


def extract_examples(prompt):
    examples = []
    lines = prompt.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "->" in line:
            parts = line.split("->")
            if len(parts) == 2:
                examples.append((parts[0].strip(), parts[1].strip()))
        elif "=" in line:
            if any(
                x in line for x in ["determine", "Below", "t =", "distance =", "for:"]
            ):
                continue
            parts = line.split("=")
            if len(parts) == 2:
                examples.append((parts[0].strip(), parts[1].strip()))
        elif "becomes" in line:
            parts = line.split("becomes")
            if len(parts) == 2:
                examples.append((parts[0].strip(), parts[1].strip()))
    return examples


def solve_physics(prompt):
    matches = re.findall(r"t = ([\d.]+)s, distance = ([\d.]+) m", prompt)
    if not matches:
        return None
    gs = [(2 * float(d)) / (float(t) ** 2) for t, d in matches if float(t) > 0]
    if not gs:
        return None
    g_avg = sum(gs) / len(gs)
    target_match = re.search(r"for t = ([\d.]+)s", prompt)
    if not target_match:
        return None
    t_target = float(target_match.group(1))
    return f"{0.5 * g_avg * (t_target**2):.2f}"


def solve_numeral(prompt):
    match = re.search(r"number (\d+)", prompt)
    if not match:
        return None
    n = int(match.group(1))
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman = ""
    for i in range(len(val)):
        while n >= val[i]:
            roman += syb[i]
            n -= val[i]
    return roman


def solve_unit(prompt):
    matches = re.findall(r"([\d.]+) m becomes ([\d.]+)", prompt)
    if not matches:
        return None
    ratios = [float(inp) / float(outp) for inp, outp in matches if float(outp) > 0]
    if not ratios:
        return None
    r_avg = sum(ratios) / len(ratios)
    target_match = re.search(r"measurement: ([\d.]+) m", prompt)
    if not target_match:
        return None
    return f"{float(target_match.group(1)) / r_avg:.2f}"


def solve_text(prompt):
    examples = extract_examples(prompt)
    char_map = {}
    words_from_ex = set()
    for inp, out in examples:
        i_words = inp.lower().split()
        o_words = out.lower().split()
        for ow in o_words:
            words_from_ex.add(ow)
        if len(i_words) == len(o_words):
            for iw, ow in zip(i_words, o_words):
                if len(iw) == len(ow):
                    for c, p in zip(iw, ow):
                        if c.isalpha() and p.isalpha():
                            if c in char_map and char_map[c] != p:
                                if isinstance(char_map[c], set):
                                    char_map[c].add(p)
                                else:
                                    char_map[c] = {char_map[c], p}
                            else:
                                char_map[c] = p

    target_match = re.search(r"text: ([a-z\s]+)$", prompt, re.I | re.M)
    if not target_match:
        return None
    target_cipher = target_match.group(1).strip().lower()

    # Constant shift heuristic
    shift_counts = {}
    for c, p in char_map.items():
        if isinstance(p, str):
            s = (ord(c) - ord(p)) % 26
            shift_counts[s] = shift_counts.get(s, 0) + 1
    if shift_counts:
        best_shift = max(shift_counts, key=shift_counts.get)
        if shift_counts[best_shift] > len(char_map) * 0.4:
            return "".join(
                [
                    (
                        chr((ord(c) - ord("a") - best_shift) % 26 + ord("a"))
                        if c.isalpha()
                        else c
                    )
                    for c in target_cipher
                ]
            )

    all_candidates = list(set(WONDERLAND_WORDS) | words_from_ex)
    all_candidates.sort(key=lambda x: (x not in words_from_ex, x))

    words = target_cipher.split()
    decoded_words = []
    for w in words:
        best_word = w
        max_matches = -1
        for candidate in all_candidates:
            if len(candidate) == len(w):
                matches = 0
                possible = True
                for c_char, p_char in zip(w, candidate):
                    if c_char in char_map:
                        mapping = char_map[c_char]
                        if isinstance(mapping, set):
                            if p_char not in mapping:
                                possible = False
                                break
                            else:
                                matches += 1
                        else:
                            if mapping != p_char:
                                possible = False
                                break
                            else:
                                matches += 1
                if possible:
                    if matches > max_matches:
                        max_matches = matches
                        best_word = candidate
                    elif (
                        matches == max_matches
                        and candidate in words_from_ex
                        and best_word not in words_from_ex
                    ):
                        best_word = candidate
        decoded_words.append(best_word)
    return " ".join(decoded_words)


def solve_equations(prompt):
    examples = extract_examples(prompt)
    target_match = re.search(r"for: (\S+)$", prompt, re.M)
    if not target_match:
        return None
    target = target_match.group(1).strip()

    num_ex = []
    for inp, out in examples:
        nums = re.findall(r"\d+", inp)
        if len(nums) == 2:
            num_ex.append(
                (int(nums[0]), int(nums[1]), out, re.sub(r"\d+", "", inp).strip())
            )

    t_nums = re.findall(r"\d+", target)
    if len(t_nums) == 2:
        tn1, tn2 = int(t_nums[0]), int(t_nums[1])
        t_op = re.sub(r"\d+", "", target).strip()

        def digit_sum(n):
            return sum(int(d) for d in str(abs(n)))

        def reverse_int(n):
            try:
                return int(str(abs(n))[::-1])
            except Exception:
                return 0

        hypotheses = [
            lambda a, b: a + b,
            lambda a, b: abs(a - b),
            lambda a, b: a * b,
            lambda a, b: a // b if b != 0 else None,
            lambda a, b: a % b if b != 0 else None,
            lambda a, b: int(str(a) + str(b)),
            lambda a, b: int(str(a)[0] + str(b)[0]) if str(a) and str(b) else None,
            lambda a, b: int(str(a)[-1] + str(b)[-1]) if str(a) and str(b) else None,
            lambda a, b: digit_sum(a) + digit_sum(b),
            lambda a, b: digit_sum(abs(a - b)),
            lambda a, b: reverse_int(a) + reverse_int(b),
            lambda a, b: abs(reverse_int(a) - reverse_int(b)),
        ]

        converters = [
            lambda v, op: str(v),
            lambda v, op: str(v) + op,
            lambda v, op: op + str(v),
            lambda v, op: str(v)[0] if str(v) else None,
            lambda v, op: str(v)[-1] if str(v) else None,
            lambda v, op: str(v)[::-1],
        ]

        for h in hypotheses:
            for conv in converters:
                consistent = True
                found_any = False
                for n1, n2, out, op in num_ex:
                    if op == t_op:
                        found_any = True
                        val = h(n1, n2)
                        if val is None or conv(val, op) != out:
                            consistent = False
                            break
                if consistent and found_any:
                    val = h(tn1, tn2)
                    if val is not None:
                        res = conv(val, t_op)
                        if res:
                            return res

    # Symbolic / Pattern substitution
    sorted_ex = sorted(examples, key=lambda x: len(x[0]), reverse=True)
    res = target
    for _ in range(5):
        changed = False
        for inp, out in sorted_ex:
            if inp in res:
                res = res.replace(inp, out)
                changed = True
                break
        if not changed:
            break

    if res == target:
        # Fallback to token/character mapping
        char_map = {}
        for inp, out in examples:
            if len(inp) == len(out):
                for c, o in zip(inp, out):
                    if c in char_map and char_map[c] != o:
                        char_map[c] = None
                    else:
                        char_map[c] = o
        char_map = {k: v for k, v in char_map.items() if v is not None}
        res = "".join([char_map.get(c, c) for c in target])

    return res


def solve_bits(prompt):
    examples = re.findall(r"([01]{8})\s*->\s*([01]{8})", prompt)
    target_match = re.search(r"for: ([01]{8})", prompt)
    if not target_match:
        return None
    target = target_match.group(1)

    X = np.array([[int(b) for b in inp] for inp, outp in examples])
    Y = np.array([[int(b) for b in outp] for inp, outp in examples])
    target_vec = np.array([int(b) for b in target])

    # Global transformations (Rotations/Inversions)
    for rot in range(8):
        for direction in [1, -1]:

            def rot_func(vec, n):
                return np.roll(vec, direction * n)

            if all(np.array_equal(rot_func(X[k], rot), Y[k]) for k in range(len(X))):
                return "".join(map(str, rot_func(target_vec, rot)))
            if all(
                np.array_equal(1 - rot_func(X[k], rot), Y[k]) for k in range(len(X))
            ):
                return "".join(map(str, 1 - rot_func(target_vec, rot)))

    res_vec = []
    for j in range(8):
        y_col = Y[:, j]
        found = False

        # 1. Linear (XOR) search - all 256 subsets
        for i in range(256):
            subset = np.array([(i >> k) & 1 for k in range(8)])
            for b_const in [0, 1]:
                if np.array_equal((X @ subset + b_const) % 2, y_col):
                    res_vec.append(int((target_vec @ subset + b_const) % 2))
                    found = True
                    break
            if found:
                break
        if found:
            continue

        # 2. 3-bit logic function search
        # Try triplets and find if any boolean function of them matches
        for i1, i2, i3 in combinations(range(8), 3):
            obs = {}
            consistent = True
            for k in range(len(X)):
                key = (X[k, i1], X[k, i2], X[k, i3])
                if key in obs and obs[key] != y_col[k]:
                    consistent = False
                    break
                obs[key] = y_col[k]
            if consistent:
                t_key = (target_vec[i1], target_vec[i2], target_vec[i3])
                if t_key in obs:
                    res_vec.append(obs[t_key])
                    found = True
                    break
                elif len(obs) >= 4:
                    # Logic patterns (Majority, Choice, etc.)
                    for bits in product([0, 1], repeat=8):
                        f = {
                            k_in: bits[idx]
                            for idx, k_in in enumerate(product([0, 1], repeat=3))
                        }
                        if all(f[k] == v for k, v in obs.items()):
                            res_vec.append(f[t_key])
                            found = True
                            break
                if found:
                    break
        if found:
            continue

        # 3. 2-bit logic fallback
        for i1, i2 in combinations(range(8), 2):
            obs = {}
            consistent = True
            for k in range(len(X)):
                key = (X[k, i1], X[k, i2])
                if key in obs and obs[key] != y_col[k]:
                    consistent = False
                    break
                obs[key] = y_col[k]
            if consistent:
                t_key = (target_vec[i1], target_vec[i2])
                if t_key in obs:
                    res_vec.append(obs[t_key])
                    found = True
                    break
                elif len(obs) >= 2:
                    for bits in product([0, 1], repeat=4):
                        f = {
                            k_in: bits[idx]
                            for idx, k_in in enumerate(product([0, 1], repeat=2))
                        }
                        if all(f[k] == v for k, v in obs.items()):
                            res_vec.append(f[t_key])
                            found = True
                            break
                if found:
                    break

        if not found:
            # Absolute fallback to identity column or original bit
            for i in range(8):
                if np.array_equal(y_col, X[:, i]):
                    res_vec.append(target_vec[i])
                    found = True
                    break
            if not found:
                res_vec.append(target_vec[j])

    return "".join(map(str, res_vec))


def wonderland_solver(prompt):
    p_lower = prompt.lower()
    if "gravitational" in p_lower:
        return solve_physics(prompt)
    elif "numeral system" in p_lower:
        return solve_numeral(prompt)
    elif "unit conversion" in p_lower:
        return solve_unit(prompt)
    elif "encryption rules" in p_lower:
        return solve_text(prompt)
    elif "applied to equations" in p_lower:
        return solve_equations(prompt)
    elif "bit manipulation rule" in p_lower:
        return solve_bits(prompt)
    return None


def get_boxed_answer(prompt):
    ans = wonderland_solver(prompt)
    return f"\\boxed{{{ans}}}" if ans else None
