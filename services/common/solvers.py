import re

import numpy as np

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
    "crystal",
    "curious",
    "dark",
    "discovers",
    "door",
    "dragon",
    "draws",
    "dreams",
    "explores",
    "follows",
    "forest",
    "found",
    "garden",
    "golden",
    "hatter",
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
]


def extract_examples(prompt):
    examples = []
    lines = prompt.split("\n")
    for line in lines:
        if "->" in line:
            parts = line.split("->")
            examples.append((parts[0].strip(), parts[1].strip()))
        elif "=" in line and "For t =" not in line and "given d =" not in line:
            parts = line.split("=")
            if len(parts) == 2:
                examples.append((parts[0].strip(), parts[1].strip()))
        elif "becomes" in line:
            parts = line.split("becomes")
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
    for inp, out in examples:
        i_words = inp.lower().split()
        o_words = out.lower().split()
        if len(i_words) == len(o_words):
            for iw, ow in zip(i_words, o_words):
                if len(iw) == len(ow):
                    for c, p in zip(iw, ow):
                        if c.isalpha() and p.isalpha():
                            char_map[c] = p

    target_match = re.search(r"text: ([a-z\s]+)$", prompt, re.I | re.M)
    if not target_match:
        return None
    target_cipher = target_match.group(1).strip().lower()

    shifts = []
    for c, p in char_map.items():
        shifts.append((ord(c) - ord(p)) % 26)
    if shifts and all(s == shifts[0] for s in shifts):
        shift = shifts[0]
        return "".join(
            [
                chr((ord(c) - ord("a") - shift) % 26 + ord("a")) if c.isalpha() else c
                for c in target_cipher
            ]
        )

    words = target_cipher.split()
    decoded_words = []
    for w in words:
        best_word = w
        max_matches = -1
        for candidate in WONDERLAND_WORDS:
            if len(candidate) == len(w):
                matches = 0
                possible = True
                for c_char, p_char in zip(w, candidate):
                    if c_char in char_map:
                        if char_map[c_char] == p_char:
                            matches += 1
                        else:
                            possible = False
                            break
                if possible and matches > max_matches:
                    max_matches = matches
                    best_word = candidate
        decoded_words.append(best_word)
    return " ".join(decoded_words)


def solve_equations(prompt):
    examples = extract_examples(prompt)
    target_match = re.search(r"for: (\S+)$", prompt, re.M)
    if not target_match:
        return None
    target = target_match.group(1).strip()

    for inp, out in examples:
        nums = re.findall(r"\d+", inp)
        if len(nums) == 2 and out.isdigit():
            n1, n2, res_val = int(nums[0]), int(nums[1]), int(out)
            t_nums = re.findall(r"\d+", target)
            if len(t_nums) == 2:
                tn1, tn2 = int(t_nums[0]), int(t_nums[1])
                if n1 + n2 == res_val:
                    return str(tn1 + tn2)
                if abs(n1 - n2) == res_val:
                    return str(abs(tn1 - tn2))
                if n1 * n2 == res_val:
                    return str(tn1 * tn2)
                if n2 != 0 and n1 // n2 == res_val:
                    return str(tn1 // tn2)

    char_map = {}
    for inp, out in examples:
        if len(inp) == len(out):
            for c1, c2 in zip(inp, out):
                char_map[c1] = c2

    sorted_examples = sorted(examples, key=lambda x: len(x[0]), reverse=True)
    res = target
    changed = True
    while changed:
        changed = False
        for inp, out in sorted_examples:
            if inp in res:
                res = res.replace(inp, out)
                changed = True
                break
        if not changed:
            new_res = "".join([char_map.get(c, c) for c in res])
            if new_res != res:
                res = new_res
                changed = True

    return res


def solve_bits(prompt):
    examples = re.findall(r"([01]{8})\s*->\s*([01]{8})", prompt)
    target_match = re.search(r"for: ([01]{8})", prompt)
    if not target_match:
        return None
    target = target_match.group(1)
    if not examples:
        return "00000000"

    X = np.array([[int(b) for b in inp] for inp, outp in examples])
    Y = np.array([[int(b) for b in outp] for inp, outp in examples])
    target_vec = np.array([int(b) for b in target])

    for rot in range(8):

        def rot_func(vec, n):
            return np.roll(vec, -n)

        if all(np.array_equal(rot_func(X[k], rot), Y[k]) for k in range(len(X))):
            return "".join(map(str, rot_func(target_vec, rot)))
        if all(np.array_equal(1 - rot_func(X[k], rot), Y[k]) for k in range(len(X))):
            return "".join(map(str, 1 - rot_func(target_vec, rot)))

    res_vec = []
    for j in range(8):
        found = False
        y_col = Y[:, j]
        for i in range(8):
            if np.array_equal(y_col, X[:, i]):
                res_vec.append(target_vec[i])
                found = True
                break
            if np.array_equal(y_col, 1 - X[:, i]):
                res_vec.append(1 - target_vec[i])
                found = True
                break

        if not found:
            X_aug = np.hstack([X, np.ones((X.shape[0], 1))])
            for i in range(512):
                bits = np.array([(i >> k) & 1 for k in range(9)])
                if np.array_equal((X_aug @ bits) % 2, y_col):
                    res_vec.append(int((np.append(target_vec, 1) @ bits) % 2))
                    found = True
                    break

        if not found:
            # Choice(x,y,z) = (x & y) ^ (~x & z)
            # Majority(x,y,z) = (x&y) ^ (y&z) ^ (x&z)
            for i1 in range(8):
                for i2 in range(8):
                    for i3 in range(8):
                        if i1 == i2 or i2 == i3 or i1 == i3:
                            continue
                        # Majority
                        maj = (
                            (X[:, i1] & X[:, i2])
                            ^ (X[:, i2] & X[:, i3])
                            ^ (X[:, i1] & X[:, i3])
                        )
                        if np.array_equal(y_col, maj):
                            res_vec.append(
                                (target_vec[i1] & target_vec[i2])
                                ^ (target_vec[i2] & target_vec[i3])
                                ^ (target_vec[i1] & target_vec[i3])
                            )
                            found = True
                            break
                        # Choice
                        ch = (X[:, i1] & X[:, i2]) ^ ((1 - X[:, i1]) & X[:, i3])
                        if np.array_equal(y_col, ch):
                            res_vec.append(
                                (target_vec[i1] & target_vec[i2])
                                ^ ((1 - target_vec[i1]) & target_vec[i3])
                            )
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

        if not found:
            res_vec.append(target_vec[j])
    return "".join(map(str, res_vec))


def wonderland_solver(prompt):
    p_lower = prompt.lower()
    res = None
    if "gravitational" in p_lower:
        res = solve_physics(prompt)
    elif "numeral system" in p_lower:
        res = solve_numeral(prompt)
    elif "unit conversion" in p_lower:
        res = solve_unit(prompt)
    elif "encryption rules" in p_lower:
        res = solve_text(prompt)
    elif "applied to equations" in p_lower:
        res = solve_equations(prompt)
    elif "bit manipulation rule" in p_lower:
        res = solve_bits(prompt)
    return res


def get_boxed_answer(prompt):
    ans = wonderland_solver(prompt)
    if ans:
        return f"\\boxed{{{ans}}}"
    return None
