"""Specific authored hooks; never manufactured statistics or exam claims."""
HOOKS = {
    "Parallel resistance": "Can parallel resistance exceed either resistor?",
    "Kinetic energy scaling": "Triple speed. Why does energy become nine times larger?",
    "Spring combination": "Two springs. Why can the pair be softer?",
    "Projectile range": "Higher launch. Longer range? Not always.",
    "Vertical throw": "At the top: zero speed or zero acceleration?",
    "Capacitor combination": "Two capacitors. Why does capacitance halve?",
    "Uniform circular motion": "Constant speed. So why is it accelerating?",
    "Wave speed": "The wave moves right. Does this dot move right?",
    "Impulse": "Same speed after a bounce. Zero impulse?",
    "Electrical power": "Double resistance. Does power rise or fall?",
    "Mole conversion": "One mole of water. How many hydrogen atoms?",
    "Dilution": "Added volume or final volume: which one belongs below?",
    "Mole fraction": "Equal moles. Unequal masses. What is mole fraction?",
    "Ideal gas ratios": "Double temperature, halve volume: pressure factor?",
    "Reaction quotient": "Large K. Can the reaction still run backwards?",
    "First-order half-life": "Three half-lives: 12.5% left or nothing left?",
    "Oxidation numbers": "Oxygen is always minus two. Can you find the exception?",
    "Limiting reagent": "More moles, but still the limiting reagent?",
    "Mass percentage": "Water evaporates. What happens to mass percent?",
    "Gas stoichiometry": "Gas volumes follow coefficients. Always?",
    "Quadratic roots": "Find a root sum without finding either root.",
    "Difference of squares": "Two huge squares. One small multiplication.",
    "Arithmetic progression": "Nine gaps. How many terms?",
    "Complementary probability": "At least one success: why count failures?",
    "Logarithm laws": "Can you split the log of a sum?",
    "Odd-function integral": "Odd function. Is its integral always zero?",
    "Even-function integral": "Symmetric bounds. Do these areas cancel?",
    "Derivative at a point": "Substitute first? That destroys the slope.",
    "Repeated percentage change": "Up 20%, down 20%. Back where you started?",
    "Vector orthogonality": "Zero dot product. Is the angle always 90 degrees?"
}

def opening(content):
    return content.get("hook") or HOOKS.get(content["topic"], content["question"])
