from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from exchange.models import PolicyRule, ExchangeRequest
from hostel.models import Bed

User = get_user_model()

class EligibilityService:
    @staticmethod
    def get_policy_int(rule_type: str, default: int) -> int:
        try:
            rule = PolicyRule.objects.filter(rule_type=rule_type, is_active=True).first()
            return rule.int_value if rule else default
        except Exception:
            return default

    @staticmethod
    def get_policy_bool(rule_type: str, default: bool) -> bool:
        try:
            rule = PolicyRule.objects.filter(rule_type=rule_type, is_active=True).first()
            return rule.bool_value if rule else default
        except Exception:
            return default

    @classmethod
    def validate_student_eligibility(cls, student: User) -> dict:
        """
        Runs comprehensive multi-point eligibility validation against active PolicyRules.
        """
        checks = []
        is_eligible = True

        # Check 1: Current Room/Bed Allocation
        try:
            bed = student.allocated_bed
            if not bed:
                checks.append({
                    'rule': 'BED_ALLOCATION',
                    'passed': False,
                    'reason': 'No current hostel bed allocation found for this student.'
                })
                is_eligible = False
            else:
                checks.append({
                    'rule': 'BED_ALLOCATION',
                    'passed': True,
                    'reason': f"Allocated bed verified: {bed.room.full_name} ({bed.bed_number})."
                })
        except Exception:
            checks.append({
                'rule': 'BED_ALLOCATION',
                'passed': False,
                'reason': 'No current hostel bed allocation found.'
            })
            is_eligible = False

        # Check 2: Cooling-off Period
        cooling_days = cls.get_policy_int(PolicyRule.RuleType.COOLING_OFF_DAYS, 30)
        if student.last_transferred_at:
            delta = timezone.now() - student.last_transferred_at
            remaining_days = cooling_days - delta.days
            if remaining_days > 0:
                is_eligible = False
                reapply_date = (student.last_transferred_at + timedelta(days=cooling_days)).strftime('%d %b %Y')
                checks.append({
                    'rule': 'COOLING_OFF',
                    'passed': False,
                    'reason': f"Cooling-off period active: {remaining_days} days remaining. Eligible on {reapply_date}."
                })
            else:
                checks.append({
                    'rule': 'COOLING_OFF',
                    'passed': True,
                    'reason': f"Cooling-off satisfied ({delta.days} days elapsed since last swap)."
                })
        else:
            checks.append({
                'rule': 'COOLING_OFF',
                'passed': True,
                'reason': "First-time exchange request (No cooling-off restriction)."
            })

        # Check 3: Fee Clearance
        fee_required = cls.get_policy_bool(PolicyRule.RuleType.FEE_CLEARANCE_REQUIRED, True)
        if fee_required:
            if not student.has_fee_clearance:
                is_eligible = False
                checks.append({
                    'rule': 'FEE_CLEARANCE',
                    'passed': False,
                    'reason': 'Hostel fee clearance pending. Please settle outstanding semester dues with accounts office.'
                })
            else:
                checks.append({
                    'rule': 'FEE_CLEARANCE',
                    'passed': True,
                    'reason': 'University hostel accounts fee clearance verified.'
                })

        # Check 4: Disciplinary Hold
        disc_check = cls.get_policy_bool(PolicyRule.RuleType.DISCIPLINARY_CHECK, True)
        if disc_check:
            if student.has_disciplinary_hold:
                is_eligible = False
                checks.append({
                    'rule': 'DISCIPLINARY_HOLD',
                    'passed': False,
                    'reason': 'Active disciplinary hold on student record. Room transfers are locked.'
                })
            else:
                checks.append({
                    'rule': 'DISCIPLINARY_HOLD',
                    'passed': True,
                    'reason': 'Good disciplinary standing (No active sanctions).'
                })

        # Check 5: Existing Pending Request
        active_request = ExchangeRequest.objects.filter(
            requester=student,
            status__in=[ExchangeRequest.RequestStatus.ACTIVE, ExchangeRequest.RequestStatus.MATCHED, ExchangeRequest.RequestStatus.PROPOSED]
        ).first()

        if active_request:
            is_eligible = False
            checks.append({
                'rule': 'CONCURRENT_REQUEST',
                'passed': False,
                'reason': f"Student already has an active exchange request (#{active_request.id}) in status '{active_request.get_status_display()}'."
            })
        else:
            checks.append({
                'rule': 'CONCURRENT_REQUEST',
                'passed': True,
                'reason': 'No conflicting active exchange requests.'
            })

        return {
            'eligible': is_eligible,
            'checks': checks
        }
