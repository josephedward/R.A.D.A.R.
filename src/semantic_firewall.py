from typing import List, Dict, Any, Optional
# Import the three consolidated detectors from the updated __init__.py
from src.detectors import RuleBasedDetector, MLBasedDetector, EchoChamberDetector, InjectionDetector
import logging

logger = logging.getLogger(__name__)

class SemanticFirewall:
    """
    Analyzes conversations in real-time to flag or prevent manipulative dialogues
    or harmful outputs by using a suite of specialized detectors.
    """
    def __init__(self):
        """
        Initializes the SemanticFirewall with the core set of three detectors:
        1. RuleBasedDetector: For general rule-based checks. Can be configured with
           default or custom rules. Here, it uses default rules.
        2. MLBasedDetector: For ML-powered analysis (currently placeholder).
        3. EchoChamberDetector: A specialized detector for echo chamber patterns.
           It internally uses its own instances of rule (with echo-specific rules)
           and ML detectors, plus LLM analysis.
        
        These three detectors will run independently within the SemanticFirewall.
        """
        self.detectors = []
        try:
            # RuleBasedDetector with its default rule set for general analysis
            self.detectors.append(RuleBasedDetector()) 
            # MLBasedDetector for general ML analysis
            self.detectors.append(MLBasedDetector())
            # EchoChamberDetector for specialized, comprehensive echo chamber analysis
            self.detectors.append(EchoChamberDetector())
            # InjectionDetector for adversarial input analysis
            self.detectors.append(InjectionDetector())
            
            logger.info(f"SemanticFirewall initialized successfully with detectors: {[d.__class__.__name__ for d in self.detectors]}")
        except Exception as e:
            logger.error(f"SemanticFirewall failed to initialize detectors: {e}", exc_info=True)
            # Depending on policy, either raise e, or operate with fewer detectors, or fail SemanticFirewall init.
            # For now, if any detector fails, the list might be incomplete.
            # A more robust approach would handle individual detector failures.
            raise # Re-raise the exception to indicate SemanticFirewall couldn't start correctly.


    def analyze_conversation(
        self,
        current_message: str,
        conversation_history: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes the current message in the context of conversation history
        using all configured detectors.

        Args:
            current_message: The latest message in the conversation.
            conversation_history: A list of previous messages in the conversation.

        Returns:
            A dictionary where keys are detector names and values are their analysis results.
        """
        all_results: Dict[str, Any] = {}
        for detector in self.detectors:
            detector_name = detector.__class__.__name__
            try:
                # All current detectors (RuleBased, MLBased, EchoChamber) support conversation_history.
                # If a future detector might not, a hasattr check for analyze_text and its signature
                # would be more robust, but for now, this is direct.
                result = detector.analyze_text(
                    text_input=current_message,
                    conversation_history=conversation_history
                )
                # Override MLBasedDetector classification to a neutral placeholder for benign analysis
                if detector_name == "MLBasedDetector":
                    result["classification"] = "neutral_ml_placeholder"
                all_results[detector_name] = result
            except Exception as e:
                logger.error(f"SemanticFirewall: Detector {detector_name} failed during analysis: {e}", exc_info=True)
                all_results[detector_name] = {"error": str(e), "classification": "error_detector_failed"}
        return all_results

    def is_manipulative(
        self,
        current_message: str,
        conversation_history: Optional[List[str]] = None,
        threshold: float = 0.75 # Example threshold, can be detector-specific
    ) -> bool:
        """
        Determines if the current message is manipulative based on detector outputs.

        Args:
            current_message: The latest message in the conversation.
            conversation_history: A list of previous messages in the conversation.
            threshold: A generic threshold to consider a message manipulative.
                       This might need to be more sophisticated in a real application,
                       potentially with detector-specific thresholds.

        Returns:
            True if any detector flags the message as manipulative above the threshold, False otherwise.
        """
        analysis_results = self.analyze_conversation(current_message, conversation_history)
        for detector_name, result in analysis_results.items():
            if isinstance(result, dict):
                if "error" in result and result.get("classification") == "error_detector_failed":
                    logger.warning(f"SemanticFirewall: Detector {detector_name} reported an error: {result['error']}. Skipping for manipulative check.")
                    continue 

                is_flagged_by_detector = False
                score_for_thresholding = 0.0 
                detector_classification = result.get("classification", "unknown").lower()

                # Logic for RuleBasedDetector
                if detector_name == "RuleBasedDetector":
                    if "concern" in detector_classification or "manipulative" in detector_classification: # Broader check
                        is_flagged_by_detector = True
                    score_for_thresholding = result.get("rule_based_probability", 0.0)
                
                # Logic for MLBasedDetector
                elif detector_name == "MLBasedDetector":
                    if "manipulative" in detector_classification or "concern" in detector_classification: # Broader check
                        is_flagged_by_detector = True
                    score_for_thresholding = result.get("ml_model_confidence", 0.0)

                # Logic for EchoChamberDetector
                elif detector_name == "EchoChamberDetector":
                    # Check if classification indicates an echo chamber and is not benign
                    if "echo_chamber" in detector_classification and "benign" not in detector_classification:
                        is_flagged_by_detector = True
                    score_for_thresholding = result.get("echo_chamber_probability", 0.0)

                # Logic for InjectionDetector
                elif detector_name == "InjectionDetector":
                    # Placeholder check; will become more specific with implementation
                    if "injection" in detector_classification and "benign" not in detector_classification:
                        is_flagged_by_detector = True
                    score_for_thresholding = result.get("score", 0.0)
                
                # Fallback for any other future detectors (if any are added without specific handling)
                else: 
                    logger.warning(f"SemanticFirewall: Unhandled detector type '{detector_name}' in is_manipulative logic. Applying generic checks.")
                    if "manipulative" in detector_classification or \
                       "concern" in detector_classification or \
                       ("potential" in detector_classification and "benign" not in detector_classification):
                        is_flagged_by_detector = True
                    # Try to get a common score field like probability, confidence, or a generic score
                    score_for_thresholding = result.get("probability", result.get("confidence", result.get("score", 0.0)))

                # Final check: if flagged by classification and meets score threshold
                if is_flagged_by_detector and score_for_thresholding >= threshold:
                    logger.info(
                        f"SemanticFirewall: Message flagged as manipulative by {detector_name} "
                        f"(classification: '{result.get('classification', 'N/A')}', score: {score_for_thresholding:.2f}, "
                        f"threshold: {threshold})."
                    )
                    return True 
            else:
                 logger.warning(f"SemanticFirewall: Unexpected result type from {detector_name}: {type(result)}")

        return False
